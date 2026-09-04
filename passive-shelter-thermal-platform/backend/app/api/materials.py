"""
FastAPI router for Material Library management.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database.base import get_db
from ..database.models import (
    Material, SimulationJob, SimulationResult, Recommendation, Report, SimulationConfig
)
from ..schemas.schemas import MaterialCreate, MaterialUpdate, MaterialResponse

router = APIRouter(prefix="/api/v1/materials", tags=["Material Library"])


@router.get("", response_model=List[MaterialResponse])
def list_materials(
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """List all materials, optionally filtered by category or search term."""
    q = db.query(Material)
    if category:
        q = q.filter(Material.category == category)
    if search:
        q = q.filter(Material.name.ilike(f"%{search}%"))
    return q.order_by(Material.name).all()


@router.get("/{material_id}", response_model=MaterialResponse)
def get_material(material_id: str, db: Session = Depends(get_db)):
    """Get a material by ID."""
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")
    return mat


@router.post("", response_model=MaterialResponse, status_code=201)
def create_material(data: MaterialCreate, db: Session = Depends(get_db)):
    """Create a new material."""
    # Check for duplicate name
    existing = db.query(Material).filter(Material.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Material '{data.name}' already exists")

    mat = Material(id=str(uuid.uuid4()), **data.model_dump())
    db.add(mat)
    db.commit()
    db.refresh(mat)
    return mat


@router.put("/{material_id}", response_model=MaterialResponse)
def update_material(material_id: str, data: MaterialUpdate, db: Session = Depends(get_db)):
    """Update an existing material."""
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(mat, field, value)

    db.commit()
    db.refresh(mat)
    return mat


@router.delete("/{material_id}", status_code=204)
def delete_material(material_id: str, db: Session = Depends(get_db)):
    """Delete a material. Cleans up referencing jobs, results, recommendations, and reports."""
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")

    # Clean up any simulation jobs referencing this material
    jobs = db.query(SimulationJob).filter(SimulationJob.material_id == material_id).all()
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

        # Delete simulation jobs referencing this material
        db.query(SimulationJob).filter(SimulationJob.material_id == material_id).delete(synchronize_session=False)

        # Remove any simulation configs that now have zero jobs remaining
        for cid in config_ids:
            remaining = db.query(SimulationJob).filter(SimulationJob.config_id == cid).count()
            if remaining == 0:
                c = db.query(SimulationConfig).filter(SimulationConfig.id == cid).first()
                if c:
                    db.delete(c)

    db.delete(mat)
    db.commit()


@router.post("/{material_id}/duplicate", response_model=MaterialResponse, status_code=201)
def duplicate_material(material_id: str, db: Session = Depends(get_db)):
    """Duplicate an existing material."""
    mat = db.query(Material).filter(Material.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")

    new_mat = Material(
        id=str(uuid.uuid4()),
        name=f"{mat.name} (Copy)",
        category=mat.category,
        description=mat.description,
        thermal_conductivity=mat.thermal_conductivity,
        density=mat.density,
        specific_heat=mat.specific_heat,
        emissivity=mat.emissivity,
        solar_absorptivity=mat.solar_absorptivity,
        solar_reflectivity=mat.solar_reflectivity,
        default_thickness=mat.default_thickness,
        notes=mat.notes,
        source=mat.source,
        is_builtin=False,
    )
    db.add(new_mat)
    db.commit()
    db.refresh(new_mat)
    return new_mat
