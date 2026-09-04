"""
Passive Thermal Shelter Simulation & Recommendation Platform
Master Launcher Script

Starts the FastAPI backend server (which serves the compiled React frontend UI
or acts as the API server for Vite dev server).
"""
import sys
import os
import subprocess
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import uvicorn
from app.config import settings

def main():
    print("=" * 70)
    print("  PASSIVE THERMAL SHELTER PLATFORM — STARTING")
    print("  PyAnsys + ANSYS MAPDL Transient Thermal Analysis Engine")
    print("=" * 70)
    print(f"  Backend API:      http://localhost:{settings.app_port}/api/docs")
    print(f"  Web Dashboard:    http://localhost:{settings.app_port}")
    print(f"  ANSYS Version:    v{settings.ansys_version}")
    print(f"  Working Storage:  {settings.data_dir}")
    print("=" * 70)
    print("  Press Ctrl+C to stop the server.\n")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=True,
        reload_dirs=[str(backend_dir)],
        app_dir=str(backend_dir),
    )

if __name__ == "__main__":
    main()
