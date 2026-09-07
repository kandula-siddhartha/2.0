"""
Simulation job worker.
Runs ANSYS simulation jobs in a background thread pool.
Updates job status in the database and broadcasts WebSocket notifications.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional

from ..database.base import get_db_context
from ..database.models import SimulationJob, SimulationResult, JobStatus
from ..mapdl_integration.thermal_runner import run_thermal_simulation, SimulationRunnerError
from ..config import settings

logger = logging.getLogger(__name__)

# Global job executor (1 concurrent ANSYS job by default for safety)
_executor: Optional[ThreadPoolExecutor] = None
_broadcast_callback: Optional[Callable] = None


def initialize_worker(max_workers: int = 1, broadcast_fn: Optional[Callable] = None) -> None:
    """Initialize the job worker thread pool."""
    global _executor, _broadcast_callback
    _executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ansys-worker")
    _broadcast_callback = broadcast_fn
    logger.info(f"[Worker] Job worker initialized (max_workers={max_workers})")


def shutdown_worker() -> None:
    """Shut down the worker thread pool."""
    global _executor
    if _executor:
        _executor.shutdown(wait=True)
        _executor = None
    logger.info("[Worker] Job worker shut down.")


def submit_job(job_id: str) -> None:
    """Submit a simulation job to the background worker."""
    global _executor
    if _executor is None:
        raise RuntimeError("Worker not initialized. Call initialize_worker() first.")
    _executor.submit(_run_job, job_id)
    logger.info(f"[Worker] Job {job_id} submitted.")


def _run_job(job_id: str) -> None:
    """
    Execute a single simulation job.
    Called in a background thread.
    """
    logger.info(f"[Worker] Starting job: {job_id}")

    with get_db_context() as db:
        job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
        if not job:
            logger.error(f"[Worker] Job {job_id} not found in database.")
            return

        # Mark as started
        job.status = JobStatus.PREPARING
        job.started_at = datetime.utcnow()
        db.flush()
        _broadcast(job)

    try:
        with get_db_context() as db:
            job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
            config = job.config
            design = job.design
            material = job.material
            weather_ds = db.query(
                __import__("app.database.models", fromlist=["WeatherDataset"]).WeatherDataset
            ).filter_by(id=config.weather_dataset_id).first()

            # Build job directory
            job_dir = str(Path(settings.simulations_dir) / job.sim_id)
            Path(job_dir).mkdir(parents=True, exist_ok=True)
            job.ansys_job_dir = job_dir
            db.flush()

            # Deserialize weather records
            from ..services.weather.weather_service import WeatherService
            ws = WeatherService()
            weather_records = ws.from_json_records(weather_ds.data_json or [])

            # Extract all scalar configuration parameters while DB session is active
            simulation_start = config.simulation_start
            simulation_end = config.simulation_end
            time_step_s = config.time_step_seconds
            mesh_size = config.mesh_size
            orientation = job.orientation
            comfort_min = config.comfort_min_temp
            comfort_max = config.comfort_max_temp
            convection_htc_override = config.convection_coefficient
            radiation_enabled = config.radiation_enabled
            solar_loading_enabled = config.solar_loading_enabled

            # Build parameter dicts
            design_params = {
                "design_type": getattr(design, "design_type", "parametric"),
                "file_path": getattr(design, "file_path", None),
                "file_format": getattr(design, "file_format", None),
                "length": design.length,
                "width": design.width,
                "height": design.height,
                "wall_thickness": design.wall_thickness,
                "roof_thickness": design.roof_thickness,
                "floor_thickness": design.floor_thickness,
            }
            material_params = {
                "name": material.name,
                "thermal_conductivity": material.thermal_conductivity,
                "density": material.density,
                "specific_heat": material.specific_heat,
                "emissivity": material.emissivity,
                "solar_absorptivity": material.solar_absorptivity,
            }

        # ── Status callback (updates DB + broadcasts) ─────────────────────────
        def on_status(status: str, message: str):
            with get_db_context() as db2:
                j = db2.query(SimulationJob).filter(SimulationJob.id == job_id).first()
                if j:
                    j.status = status
                    j.progress_message = message
                    db2.flush()
                    _broadcast(j)

        # ── Run the simulation ─────────────────────────────────────────────────
        results = run_thermal_simulation(
            job_id=job_id,
            job_dir=job_dir,
            design_params=design_params,
            material_params=material_params,
            weather_records=weather_records,
            simulation_start=simulation_start,
            simulation_end=simulation_end,
            time_step_s=time_step_s,
            mesh_size=mesh_size,
            orientation=orientation,
            comfort_min=comfort_min,
            comfort_max=comfort_max,
            convection_htc_override=convection_htc_override,
            radiation_enabled=radiation_enabled,
            solar_loading_enabled=solar_loading_enabled,
            status_callback=on_status,
        )

        # ── Store results ──────────────────────────────────────────────────────
        with get_db_context() as db:
            job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
            metrics = results.get("scalar_metrics", {})
            mesh_info = results.get("mesh_info", {})

            # Convert times to ISO timestamps
            start_dt = simulation_start
            import json

            timestamps = []
            for t_s in results.get("times_s", []):
                from datetime import timedelta
                ts = start_dt + timedelta(seconds=t_s)
                timestamps.append(ts.isoformat())

            sim_result = SimulationResult(
                job_id=job_id,
                timestamps=timestamps,
                temp_internal=results.get("temp_internal_avg", []),
                temp_ambient=results.get("ambient_temps", []),
                solar_radiation=results.get("solar_radiation", []),
                solar_heat_gain=results.get("solar_heat_gain_w", []),
                total_heat_flow=results.get("total_heat_flow_w", []),
                min_internal_temp=metrics.get("min_internal_temp"),
                max_internal_temp=metrics.get("max_internal_temp"),
                avg_internal_temp=metrics.get("avg_internal_temp"),
                nighttime_min_temp=metrics.get("nighttime_min_temp"),
                nighttime_avg_temp=metrics.get("nighttime_avg_temp"),
                comfort_hours=metrics.get("comfort_hours"),
                comfort_percentage=metrics.get("comfort_percentage"),
                total_solar_gain_kwh=results.get("total_solar_gain_kwh"),
                total_heat_loss_kwh=results.get("total_heat_loss_kwh"),
                peak_heat_loss_w=results.get("peak_heat_loss_w"),
                temp_fluctuation_std=metrics.get("temp_fluctuation_std"),
                nighttime_retention_score=metrics.get("nighttime_retention_score"),
                node_count=mesh_info.get("node_count"),
                element_count=mesh_info.get("element_count"),
                solve_time_seconds=results.get("solve_time_s"),
                contour_3d=results.get("contour_3d"),
            )
            db.add(sim_result)

            job.status = JobStatus.COMPLETED
            job.progress_message = "Simulation complete. Results stored."
            job.completed_at = datetime.utcnow()
            job.ansys_version_used = results.get("ansys_version", "")
            db.flush()
            _broadcast(job)

        logger.info(f"[Worker] Job {job_id} COMPLETED.")

        # Clean up heavy MAPDL FEA scratch files (.rth, .db, .full) to prevent disk bloat
        try:
            p_dir = Path(job_dir)
            if p_dir.exists():
                for ext in {".rth", ".db", ".rdb", ".full", ".esav", ".ldhi", ".r001", ".dsp", ".mntr", ".err", ".out"}:
                    for f in p_dir.glob(f"*{ext}"):
                        try:
                            f.unlink()
                        except Exception:
                            pass
        except Exception:
            pass

    except SimulationRunnerError as e:
        logger.error(f"[Worker] Job {job_id} FAILED: {e}")
        with get_db_context() as db:
            job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                db.flush()
                _broadcast(job)

    except Exception as e:
        logger.exception(f"[Worker] Job {job_id} FAILED with unexpected error: {e}")
        with get_db_context() as db:
            job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = f"Unexpected error: {e}"
                job.completed_at = datetime.utcnow()
                db.flush()
                _broadcast(job)


def _broadcast(job: SimulationJob) -> None:
    """Broadcast job status update via WebSocket."""
    global _broadcast_callback
    if _broadcast_callback:
        try:
            msg = {
                "type": "job_update",
                "payload": {
                    "job_id": job.id,
                    "sim_id": job.sim_id,
                    "status": job.status,
                    "progress_message": job.progress_message,
                    "error_message": job.error_message,
                },
            }
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.ensure_future(_broadcast_callback(msg))
            )
        except Exception as e:
            logger.debug(f"[Worker] Broadcast error: {e}")
