"""
FastAPI router for PDF report generation.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database.base import get_db
from ..database.models import (
    Recommendation, SimulationJob, SimulationResult,
    SimulationConfig, WeatherDataset, Location, Design, Material, Report
)
from ..services.report_service import ReportService
from ..config import settings

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])
_report_svc = ReportService()


@router.post("/generate/{recommendation_id}", response_model=dict)
def generate_report(recommendation_id: str, db: Session = Depends(get_db)):
    """Generate a PDF report for a recommendation."""
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec_job = db.query(SimulationJob).filter(SimulationJob.id == rec.recommended_job_id).first()
    config = rec_job.config if rec_job else None
    weather = db.query(WeatherDataset).filter(
        WeatherDataset.id == (config.weather_dataset_id if config else None)
    ).first() if config else None
    location = db.query(Location).filter(
        Location.id == (config.location_id if config else None)
    ).first() if config else None
    rec_result = db.query(SimulationResult).filter(
        SimulationResult.job_id == rec.recommended_job_id
    ).first()

    # Build all comparison data
    from ..database.models import JobStatus
    all_jobs = db.query(SimulationJob).filter(
        SimulationJob.config_id == config.id if config else False
    ).all() if config else []

    comparison_table = []
    for j in all_jobs:
        r = db.query(SimulationResult).filter(SimulationResult.job_id == j.id).first()
        comparison_table.append({
            "sim_id": j.sim_id,
            "design_name": j.design.name if j.design else "?",
            "material_name": j.material.name if j.material else "?",
            "avg_internal_temp": getattr(r, "avg_internal_temp", None) if r else None,
            "min_internal_temp": getattr(r, "min_internal_temp", None) if r else None,
            "comfort_percentage": getattr(r, "comfort_percentage", None) if r else None,
            "total_solar_gain_kwh": getattr(r, "total_solar_gain_kwh", None) if r else None,
            "total_heat_loss_kwh": getattr(r, "total_heat_loss_kwh", None) if r else None,
            "score": (rec.all_scores or {}).get(j.id),
            "is_recommended": j.id == rec.recommended_job_id,
        })
    comparison_table.sort(key=lambda x: x.get("score") or 0, reverse=True)

    # Build weather summary
    weather_records = []
    if weather and weather.data_json:
        weather_records = weather.data_json
    temps = [r.get("temperature_2m") for r in weather_records if r.get("temperature_2m") is not None]
    solar = [r.get("shortwave_radiation") for r in weather_records if r.get("shortwave_radiation") is not None]
    wind = [r.get("wind_speed_10m") for r in weather_records if r.get("wind_speed_10m") is not None]

    report_data = {
        "title": f"Passive Thermal Shelter Analysis — {location.name if location else 'Location'}",
        "location_name": location.display_name if location else "—",
        "total_combinations": len(all_jobs),
        "recommended_label": (
            f"{rec_job.design.name} + {rec_job.material.name}"
            if rec_job and rec_job.design and rec_job.material else "—"
        ),
        "overall_score": rec.overall_score,
        "explanation": rec.explanation or [],
        "weather_provider": weather.provider if weather else "Open-Meteo",
        "ansys_version": getattr(rec_job, "ansys_version_used", "26.1") if rec_job else "26.1",
        "pymapdl_version": "0.74.1",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "environment": {
            "location_name": location.name if location else "—",
            "latitude": location.latitude if location else "—",
            "longitude": location.longitude if location else "—",
            "elevation": location.elevation if location else "—",
            "timezone": location.timezone if location else "—",
            "simulation_period": (
                f"{config.simulation_start.strftime('%Y-%m-%d %H:%M')} to "
                f"{config.simulation_end.strftime('%Y-%m-%d %H:%M')}"
            ) if config else "—",
            "peak_solar": f"{max(solar):.0f}" if solar else "—",
            "temp_min": f"{min(temps):.1f}" if temps else "—",
            "temp_max": f"{max(temps):.1f}" if temps else "—",
            "wind_min": f"{min(wind):.1f}" if wind else "—",
            "wind_max": f"{max(wind):.1f}" if wind else "—",
        },
        "simulation_settings": {
            "mesh_size": config.mesh_size if config else "—",
            "time_step_s": config.time_step_seconds if config else "—",
            "duration_h": (
                (config.simulation_end - config.simulation_start).total_seconds() / 3600
            ) if config else "—",
            "solar_enabled": config.solar_loading_enabled if config else True,
            "radiation_enabled": config.radiation_enabled if config else True,
            "comfort_min": config.comfort_min_temp if config else 18,
            "comfort_max": config.comfort_max_temp if config else 27,
        },
        "comparison_table": comparison_table,
        "recommendation_weights": rec.weights_used,
    }

    output_path = str(
        Path(settings.reports_dir) / f"report_{recommendation_id[:8]}.pdf"
    )
    try:
        pdf_path = _report_svc.generate_report(report_data, output_path=output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")

    # Store report record
    file_size = Path(pdf_path).stat().st_size if Path(pdf_path).exists() else 0
    report = Report(
        id=str(uuid.uuid4()),
        recommendation_id=recommendation_id,
        title=report_data["title"],
        file_path=pdf_path,
        file_size_bytes=file_size,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "title": report.title,
        "file_path": pdf_path,
        "file_size_bytes": file_size,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/download/{report_id}")
def download_report(report_id: str, db: Session = Depends(get_db)):
    """Download a generated PDF report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not Path(report.file_path).exists():
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=Path(report.file_path).name,
    )
