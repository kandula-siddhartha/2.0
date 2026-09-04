"""
Passive Thermal Shelter Thermal Analysis Platform
FastAPI Backend Application

Architecture:
    React Frontend → FastAPI Backend → PyMAPDL → ANSYS MAPDL → Results → Dashboard
"""
from __future__ import annotations

import asyncio
import json
import importlib
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database.init_db import init_db
from .api import locations, materials, designs, simulations, ansys, reports
from .worker.job_worker import initialize_worker, shutdown_worker

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ─── WebSocket connection manager ─────────────────────────────────────────────
class ConnectionManager:
    """Manages active WebSocket connections for real-time status updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.add(ws)
        logger.info(f"[WS] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, ws: WebSocket):
        self.active_connections.discard(ws)
        logger.info(f"[WS] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        msg_str = json.dumps(message)
        dead = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(msg_str)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections.discard(ws)


manager = ConnectionManager()


# ─── Application lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and worker on startup; clean up on shutdown."""
    logger.info("=" * 60)
    logger.info("  Passive Thermal Shelter Platform — Starting")
    logger.info("=" * 60)

    # Initialize database
    logger.info("[Init] Initializing database...")
    init_db()

    # Initialize job worker
    async def broadcast_fn(msg: dict):
        await manager.broadcast(msg)

    initialize_worker(
        max_workers=settings.max_concurrent_simulations,
        broadcast_fn=broadcast_fn,
    )
    logger.info(f"[Init] Job worker ready (max concurrent: {settings.max_concurrent_simulations})")
    logger.info(f"[Init] Application ready. Open http://localhost:{settings.app_port}")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("[Shutdown] Stopping job worker...")
    shutdown_worker()
    logger.info("[Shutdown] Done.")


# ─── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Passive Thermal Shelter Analysis Platform",
    description=(
        "PyAnsys-powered thermal simulation and design recommendation system "
        "for passive shelters in high-altitude cold regions."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(locations.router)
app.include_router(materials.router)
app.include_router(designs.router)
app.include_router(simulations.router)
app.include_router(ansys.router)
app.include_router(reports.router)


# ─── WebSocket endpoint ────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time simulation status updates."""
    await manager.connect(websocket)
    try:
        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "connected",
            "payload": {"message": "Connected to Passive Thermal Shelter Platform"},
        }))
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo back ping messages
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "payload": {}}))
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_text(json.dumps({"type": "keepalive", "payload": {}}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Passive Thermal Shelter Platform",
        "version": "1.0.0",
    }


@app.get("/api/v1/system/info")
def system_info():
    """Return system configuration information."""
    _pymapdl = importlib.import_module("ansys.mapdl.core")
    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "pymapdl_version": _pymapdl.__version__,
        "ansys_install_path": settings.ansys_install_path,
        "ansys_version": settings.ansys_version,
        "max_concurrent_simulations": settings.max_concurrent_simulations,
        "data_dir": str(Path(settings.data_dir).absolute()),
    }


# ─── Serve frontend build (Single Page Application Fallback) ────────────────
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
assets_dir = frontend_dist / "assets"

if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve static files or fallback to index.html for React Router routes."""
    # Check if exact file exists in frontend_dist (e.g. favicon, vite.svg)
    file_path = frontend_dist / full_path
    if full_path and file_path.is_file():
        return FileResponse(file_path)

    # Catch-all fallback to index.html for client-side routing
    index_file = frontend_dist / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Frontend build index.html not found")
