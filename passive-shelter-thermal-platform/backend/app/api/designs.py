"""
FastAPI router for Design Library management with file upload support.
"""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database.base import get_db
from ..database.models import (
    Design, SimulationJob, SimulationResult, Recommendation, Report, SimulationConfig
)
from ..schemas.schemas import DesignCreate, DesignResponse
from ..config import settings

router = APIRouter(prefix="/api/v1/designs", tags=["Design Library"])

ALLOWED_EXTENSIONS = {".step", ".stp", ".iges", ".igs", ".stl", ".cdb", ".ans"}


@router.get("", response_model=List[DesignResponse])
def list_designs(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all shelter designs."""
    q = db.query(Design)
    if search:
        q = q.filter(Design.name.ilike(f"%{search}%"))
    return q.order_by(Design.name).all()


@router.get("/{design_id}", response_model=DesignResponse)
def get_design(design_id: str, db: Session = Depends(get_db)):
    """Get a design by ID."""
    d = db.query(Design).filter(Design.id == design_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Design not found")
    return d


@router.post("", response_model=DesignResponse, status_code=201)
def create_design(data: DesignCreate, db: Session = Depends(get_db)):
    """Create a new parametric shelter design."""
    payload = data.model_dump()
    payload.pop("design_type", None)
    d = Design(
        id=str(uuid.uuid4()),
        design_type="parametric",
        floor_area=data.length * data.width,
        volume=data.length * data.width * data.height,
        **payload,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.post("/upload", response_model=DesignResponse, status_code=201)
async def upload_design(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(default=""),
    length: float = Form(default=5.0),
    width: float = Form(default=4.0),
    height: float = Form(default=3.0),
    wall_thickness: float = Form(default=0.3),
    roof_thickness: float = Form(default=0.25),
    floor_thickness: float = Form(default=0.2),
    orientation: str = Form(default="south"),
    notes: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Upload an external geometry file (STEP, IGES, STL, etc.)."""
    ext = Path(file.filename).suffix.lower()
    if ext in {".dsco", ".scdoc"}:
        raise HTTPException(
            status_code=400,
            detail="ANSYS Discovery (.dsco) / SpaceClaim (.scdoc) are proprietary session project files. Please open your model in ANSYS Discovery / SpaceClaim and choose 'File' -> 'Export' (or 'Save As') -> 'STEP (*.step, *.stp)' or 'ANSYS Common Database (*.cdb)' to simulate in MAPDL."
        )
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Save file
    design_id = str(uuid.uuid4())
    save_dir = Path(settings.designs_dir) / design_id
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / file.filename

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # ── Auto-extract true 3D bounding span & volume from CAD geometry ─────────
    cad_volume = None
    if ext in {".step", ".stp", ".iges", ".igs", ".stl", ".brep"}:
        try:
            import gmsh
            gmsh.initialize(interruptible=False)
            try:
                gmsh.option.setNumber("General.Terminal", 0)
                gmsh.open(str(file_path))
                bbox = gmsh.model.getBoundingBox(-1, -1)
                dx = float(bbox[3] - bbox[0])
                dy = float(bbox[4] - bbox[1])
                dz = float(bbox[5] - bbox[2])

                scale = 1.0
                # Handle millimeter to meter normalization
                if max(dx, dy, dz) > 100.0:
                    scale = 0.001
                    dx *= 0.001
                    dy *= 0.001
                    dz *= 0.001

                if dx > 0.01 and dy > 0.01 and dz > 0.01:
                    length = round(dx, 2)
                    width = round(dy, 2)
                    height = round(dz, 2)

                # Query exact solid volume from OpenCASCADE
                vols = gmsh.model.getEntities(3)
                if vols:
                    raw_vol = sum(gmsh.model.occ.getMass(dim, tag) for dim, tag in vols)
                    if raw_vol > 0:
                        cad_volume = round(raw_vol * (scale ** 3), 2)
            finally:
                gmsh.finalize()
        except Exception as e:
            # Fallback to user-provided form dimensions if extraction encounters an issue
            pass

    d = Design(
        id=design_id,
        name=name,
        description=description or None,
        design_type="imported",
        file_path=str(file_path),
        file_format=ext.lstrip(".").upper(),
        file_size_bytes=len(content),
        length=length,
        width=width,
        height=height,
        wall_thickness=wall_thickness,
        roof_thickness=roof_thickness,
        floor_thickness=floor_thickness,
        floor_area=round(length * width, 2),
        volume=cad_volume if cad_volume is not None else round(length * width * height, 2),
        orientation=orientation,
        notes=notes or None,
        is_builtin=False,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.put("/{design_id}", response_model=DesignResponse)
def update_design(design_id: str, data: DesignCreate, db: Session = Depends(get_db)):
    """Update a design."""
    d = db.query(Design).filter(Design.id == design_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Design not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(d, field, value)
    d.floor_area = d.length * d.width
    d.volume = d.length * d.width * d.height

    db.commit()
    db.refresh(d)
    return d


@router.delete("/{design_id}", status_code=204)
def delete_design(design_id: str, db: Session = Depends(get_db)):
    """Delete a design. Cleans up referencing jobs, results, recommendations, and files."""
    d = db.query(Design).filter(Design.id == design_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Design not found")

    # Clean up any simulation jobs referencing this design
    jobs = db.query(SimulationJob).filter(SimulationJob.design_id == design_id).all()
    job_ids = [j.id for j in jobs]
    config_ids = list({j.config_id for j in jobs})

    if job_ids:
        # Delete recommendations and reports for these jobs
        recs = db.query(Recommendation).filter(Recommendation.recommended_job_id.in_(job_ids)).all()
        rec_ids = [r.id for r in recs]
        if rec_ids:
            reports = db.query(Report).filter(Report.recommendation_id.in_(rec_ids)).all()
            for rep in reports:
                if rep.file_path:
                    try:
                        Path(rep.file_path).unlink(missing_ok=True)
                    except Exception:
                        pass
                db.delete(rep)
            for r in recs:
                db.delete(r)

        # Delete simulation results
        db.query(SimulationResult).filter(SimulationResult.job_id.in_(job_ids)).delete(synchronize_session=False)

        # Cleanup workspace directories
        for job in jobs:
            if job.ansys_job_dir:
                try:
                    shutil.rmtree(job.ansys_job_dir, ignore_errors=True)
                except Exception:
                    pass

        # Delete simulation jobs referencing this design
        db.query(SimulationJob).filter(SimulationJob.design_id == design_id).delete(synchronize_session=False)

        # Remove any simulation configs that now have zero jobs remaining
        for cid in config_ids:
            remaining = db.query(SimulationJob).filter(SimulationJob.config_id == cid).count()
            if remaining == 0:
                c = db.query(SimulationConfig).filter(SimulationConfig.id == cid).first()
                if c:
                    db.delete(c)

    if d.file_path:
        try:
            p = Path(d.file_path)
            if p.exists():
                p.unlink(missing_ok=True)
                if p.parent != Path(settings.designs_dir) and p.parent.exists():
                    p.parent.rmdir()
        except Exception:
            pass

    db.delete(d)
    db.commit()


@router.post("/{design_id}/duplicate", response_model=DesignResponse, status_code=201)
def duplicate_design(design_id: str, db: Session = Depends(get_db)):
    """Duplicate a design."""
    d = db.query(Design).filter(Design.id == design_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Design not found")

    new_d = Design(
        id=str(uuid.uuid4()),
        name=f"{d.name} (Copy)",
        description=d.description,
        design_type=d.design_type,
        length=d.length,
        width=d.width,
        height=d.height,
        wall_thickness=d.wall_thickness,
        roof_thickness=d.roof_thickness,
        floor_thickness=d.floor_thickness,
        floor_area=d.floor_area,
        volume=d.volume,
        window_area=d.window_area,
        door_area=d.door_area,
        window_orientation=d.window_orientation,
        glazing_u_value=d.glazing_u_value,
        orientation=d.orientation,
        notes=d.notes,
        is_builtin=False,
    )
    db.add(new_d)
    db.commit()
    db.refresh(new_d)
    return new_d
