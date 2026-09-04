"""
FastAPI router for simulation management.
Handles simulation configuration creation, job launching, and status monitoring.
"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..database.base import get_db
from ..database.models import (
    SimulationConfig, SimulationJob, SimulationResult,
    Location, WeatherDataset, Design, Material, Recommendation, Report, JobStatus
)
from ..schemas.schemas import (
    SimulationConfigCreate, SimulationJobResponse,
    SimulationResultResponse, RecommendationResponse,
)
from ..worker.job_worker import submit_job
from ..services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/v1/simulations", tags=["Simulations"])

_sim_counter = 0


def _next_sim_id(db: Session) -> str:
    """Generate guaranteed unique simulation ID."""
    count = db.query(SimulationJob).count()
    year = datetime.utcnow().year
    suffix = uuid.uuid4().hex[:4].upper()
    return f"SIM-{year}-{count + 1:04d}-{suffix}"


@router.post("/configure", response_model=dict, status_code=201)
def configure_simulation(data: SimulationConfigCreate, db: Session = Depends(get_db)):
    """
    Configure a simulation batch.
    Generates all design × material combinations as simulation jobs.
    """
    # Validate location
    loc = db.query(Location).filter(Location.id == data.location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    # Validate weather dataset
    wd = db.query(WeatherDataset).filter(WeatherDataset.id == data.weather_dataset_id).first()
    if not wd:
        raise HTTPException(status_code=404, detail="Weather dataset not found")

    # Validate designs
    designs = db.query(Design).filter(Design.id.in_(data.design_ids)).all()
    if len(designs) != len(data.design_ids):
        raise HTTPException(status_code=404, detail="One or more designs not found")

    # Validate materials
    materials = db.query(Material).filter(Material.id.in_(data.material_ids)).all()
    if len(materials) != len(data.material_ids):
        raise HTTPException(status_code=404, detail="One or more materials not found")

    # Create simulation config
    config = SimulationConfig(
        id=str(uuid.uuid4()),
        name=(data.name.strip() if data.name and data.name.strip() else f"Simulation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"),
        location_id=data.location_id,
        weather_dataset_id=data.weather_dataset_id,
        simulation_start=data.simulation_start,
        simulation_end=data.simulation_end,
        time_step_seconds=data.time_step_seconds,
        mesh_size=data.mesh_size,
        convection_coefficient=data.convection_coefficient,
        radiation_enabled=data.radiation_enabled,
        solar_loading_enabled=data.solar_loading_enabled,
        thermal_mass_enabled=data.thermal_mass_enabled,
        comfort_min_temp=data.comfort_min_temp,
        comfort_max_temp=data.comfort_max_temp,
        num_occupants=data.num_occupants,
        heat_per_occupant=data.heat_per_occupant,
        recommendation_weights=data.recommendation_weights.model_dump(),
    )
    db.add(config)
    db.flush()

    # Generate all combinations: design × material
    jobs = []
    for design in designs:
        for material in materials:
            job = SimulationJob(
                id=str(uuid.uuid4()),
                sim_id=_next_sim_id(db),
                config_id=config.id,
                design_id=design.id,
                material_id=material.id,
                orientation=data.orientation,
                status=JobStatus.QUEUED,
            )
            db.add(job)
            jobs.append(job)

    db.commit()

    return {
        "config_id": config.id,
        "total_jobs": len(jobs),
        "job_ids": [j.id for j in jobs],
        "combinations": [
            {
                "job_id": j.id,
                "sim_id": j.sim_id,
                "design": j.design.name,
                "material": j.material.name,
                "orientation": j.orientation,
            }
            for j in jobs
        ],
    }


@router.post("/launch/{config_id}", response_model=dict)
def launch_simulations(config_id: str, db: Session = Depends(get_db)):
    """Launch all queued jobs for a simulation configuration."""
    config = db.query(SimulationConfig).filter(SimulationConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Simulation config not found")

    queued_jobs = db.query(SimulationJob).filter(
        SimulationJob.config_id == config_id,
        SimulationJob.status == JobStatus.QUEUED,
    ).all()

    if not queued_jobs:
        raise HTTPException(status_code=400, detail="No queued jobs found for this configuration")

    launched = []
    for job in queued_jobs:
        try:
            submit_job(job.id)
            launched.append(job.id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to launch job {job.sim_id}: {e}")

    return {
        "launched": len(launched),
        "job_ids": launched,
    }


@router.get("/configs", response_model=List[dict])
def list_configs(db: Session = Depends(get_db)):
    """List all simulation configurations with status counts."""
    configs = db.query(SimulationConfig).order_by(SimulationConfig.created_at.desc()).all()
    out = []
    for c in configs:
        jobs = db.query(SimulationJob).filter(SimulationJob.config_id == c.id).all()
        completed = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
        failed = sum(1 for j in jobs if j.status == JobStatus.FAILED)
        out.append({
            "id": c.id,
            "name": c.name,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "total_jobs": len(jobs),
            "completed_jobs": completed,
            "failed_jobs": failed,
            "comfort_min_temp": c.comfort_min_temp if c.comfort_min_temp is not None else 18.0,
            "comfort_max_temp": c.comfort_max_temp if c.comfort_max_temp is not None else 27.0,
        })
    return out


@router.get("/latest-config", response_model=dict)
def get_latest_config(db: Session = Depends(get_db)):
    """Get the most recent simulation configuration that has completed jobs."""
    # Find newest config that has completed jobs
    configs = db.query(SimulationConfig).order_by(SimulationConfig.created_at.desc()).all()
    for c in configs:
        completed = db.query(SimulationJob).filter(
            SimulationJob.config_id == c.id,
            SimulationJob.status == JobStatus.COMPLETED
        ).count()
        if completed > 0:
            return {"config_id": c.id, "name": c.name, "completed_jobs": completed}

    # Fallback to any config
    if configs:
        return {"config_id": configs[0].id, "name": configs[0].name, "completed_jobs": 0}

    raise HTTPException(status_code=404, detail="No simulation configurations found")


@router.get("/jobs/{config_id}", response_model=List[SimulationJobResponse])
def list_jobs(config_id: str, db: Session = Depends(get_db)):
    """List all simulation jobs for a configuration."""
    return db.query(SimulationJob).filter(SimulationJob.config_id == config_id).all()


@router.get("/job/{job_id}", response_model=SimulationJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a specific simulation job."""
    job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/result/{job_id}", response_model=SimulationResultResponse)
def get_result(job_id: str, db: Session = Depends(get_db)):
    """Get results for a completed simulation job."""
    result = db.query(SimulationResult).filter(SimulationResult.job_id == job_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="No result found. Simulation may not be complete.")
    return result


@router.post("/recommend/{config_id}", response_model=dict)
def generate_recommendation(config_id: str, db: Session = Depends(get_db)):
    """Generate the Recommended Configuration from completed simulations."""
    config = db.query(SimulationConfig).filter(SimulationConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    completed_jobs = db.query(SimulationJob).filter(
        SimulationJob.config_id == config_id,
        SimulationJob.status == JobStatus.COMPLETED,
    ).all()

    if not completed_jobs:
        raise HTTPException(status_code=400, detail="No completed simulations to evaluate")

    # Build job_results for recommendation engine
    job_results = []
    for job in completed_jobs:
        result = db.query(SimulationResult).filter(SimulationResult.job_id == job.id).first()
        if result:
            job_results.append({
                "job_id": job.id,
                "sim_id": job.sim_id,
                "design_name": job.design.name,
                "material_name": job.material.name,
                "result": result,
            })

    if not job_results:
        raise HTTPException(status_code=400, detail="No result data available for completed jobs")

    # Run recommendation engine
    svc = RecommendationService()
    c_min = config.comfort_min_temp if config.comfort_min_temp is not None else 18.0
    c_max = config.comfort_max_temp if config.comfort_max_temp is not None else 27.0
    rec_data = svc.generate_recommendation(
        job_results=job_results,
        weights=config.recommendation_weights,
        comfort_min=c_min,
        comfort_max=c_max,
    )

    # Store recommendation
    session_id = str(uuid.uuid4())
    rec = Recommendation(
        id=str(uuid.uuid4()),
        session_id=session_id,
        recommended_job_id=rec_data["recommended_job_id"],
        overall_score=rec_data["overall_score"],
        weights_used=rec_data["weights_used"],
        scores_breakdown=rec_data["scores_breakdown"],
        explanation=rec_data["explanation"],
        all_scores=rec_data["all_scores"],
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Build response with full detail
    rec_job = db.query(SimulationJob).filter(
        SimulationJob.id == rec_data["recommended_job_id"]
    ).first()
    rec_result = db.query(SimulationResult).filter(
        SimulationResult.job_id == rec_data["recommended_job_id"]
    ).first()

    # Build comparison table
    comparison = []
    for jr in job_results:
        jid = jr["job_id"]
        r = jr["result"]
        t_int = getattr(r, "temp_internal", None)
        if t_int and len(t_int) > 0:
            c_pct = round((sum(1 for t in t_int if c_min <= t <= c_max) / len(t_int)) * 100.0, 1)
        else:
            c_pct = getattr(r, "comfort_percentage", None)

        comparison.append({
            "job_id": jid,
            "sim_id": next((j.sim_id for j in completed_jobs if j.id == jid), ""),
            "design_name": jr["design_name"],
            "material_name": jr["material_name"],
            "avg_internal_temp": getattr(r, "avg_internal_temp", None),
            "min_internal_temp": getattr(r, "min_internal_temp", None),
            "max_internal_temp": getattr(r, "max_internal_temp", None),
            "comfort_percentage": c_pct,
            "total_solar_gain_kwh": getattr(r, "total_solar_gain_kwh", None),
            "total_heat_loss_kwh": getattr(r, "total_heat_loss_kwh", None),
            "nighttime_retention_score": getattr(r, "nighttime_retention_score", None),
            "score": rec_data["all_scores"].get(jid),
            "is_recommended": jid == rec_data["recommended_job_id"],
        })

    # Sort by score descending
    comparison.sort(key=lambda x: x.get("score", 0) or 0, reverse=True)

    return {
        "recommendation_id": rec.id,
        "session_id": session_id,
        "recommended_job_id": rec_data["recommended_job_id"],
        "recommended_design": rec_job.design.name if rec_job else None,
        "recommended_material": rec_job.material.name if rec_job else None,
        "overall_score": rec_data["overall_score"],
        "explanation": rec_data["explanation"],
        "weights_used": rec_data["weights_used"],
        "scores_breakdown": rec_data["scores_breakdown"].get(rec_data["recommended_job_id"]),
        "comparison_table": comparison,
        "total_completed": len(completed_jobs),
        "total_failed": db.query(SimulationJob).filter(
            SimulationJob.config_id == config_id,
            SimulationJob.status == JobStatus.FAILED,
        ).count(),
        "comfort_min_temp": c_min,
        "comfort_max_temp": c_max,
    }


@router.delete("/job/{job_id}/cancel", response_model=dict)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel a queued job."""
    job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in [JobStatus.QUEUED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in status {job.status}. Only QUEUED jobs can be cancelled."
        )
    job.status = JobStatus.CANCELLED
    db.commit()
    return {"message": f"Job {job.sim_id} cancelled.", "job_id": job_id}


@router.delete("/configs/{config_id}", status_code=204)
def delete_config(config_id: str, db: Session = Depends(get_db)):
    """Delete a simulation configuration and all associated jobs, results, recommendations, and reports."""
    config = db.query(SimulationConfig).filter(SimulationConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Simulation configuration not found")

    jobs = db.query(SimulationJob).filter(SimulationJob.config_id == config_id).all()
    job_ids = [j.id for j in jobs]

    if job_ids:
        # Delete reports referencing recommendations of these jobs
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

        # Cleanup disk directories
        for job in jobs:
            if job.ansys_job_dir:
                try:
                    shutil.rmtree(job.ansys_job_dir, ignore_errors=True)
                except Exception:
                    pass

        # Delete simulation jobs
        db.query(SimulationJob).filter(SimulationJob.config_id == config_id).delete(synchronize_session=False)

    db.delete(config)
    db.commit()
