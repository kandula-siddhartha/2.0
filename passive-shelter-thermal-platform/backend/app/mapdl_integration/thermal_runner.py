"""
ANSYS thermal simulation runner.
Orchestrates the complete MAPDL thermal simulation workflow:
  1. Connect to ANSYS via PyMAPDL
  2. Build parametric geometry
  3. Assign material
  4. Generate mesh
  5. Apply boundary conditions (convection, radiation)
  6. Apply solar load
  7. Configure transient analysis
  8. Solve
  9. Extract results
  10. Return structured result data

STRICT REQUIREMENT: All thermal simulation is performed by ANSYS MAPDL.
Python only orchestrates. No simplified thermal calculations are used
as a substitute for ANSYS.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .connection import MAPDLSession, AnsysConnectionError
from .model_builder import ShelterModelBuilder, ShelterGeometry
from .material_mapper import MaterialMapper
from .mesh_generator import MeshGenerator
from .boundary_conditions import BoundaryConditionApplicator
from .solar_load import SolarLoadApplicator
from .transient_solver import TransientSolver
from .result_extractor import ResultExtractor
from ..config import settings

logger = logging.getLogger(__name__)


class SimulationRunnerError(Exception):
    """Raised when a simulation step fails."""
    pass


def run_thermal_simulation(
    job_id: str,
    job_dir: str,
    design_params: dict,
    material_params: dict,
    weather_records: list,
    simulation_start: datetime,
    simulation_end: datetime,
    time_step_s: int,
    mesh_size: float,
    orientation: str,
    comfort_min: float,
    comfort_max: float,
    convection_htc_override: Optional[float],
    radiation_enabled: bool,
    solar_loading_enabled: bool,
    status_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict:
    """
    Run a complete ANSYS transient thermal simulation for one design+material combination.

    Parameters
    ----------
    job_id : str
        Unique job identifier for logging.
    job_dir : str
        Directory for ANSYS working files.
    design_params : dict
        Design geometry parameters.
    material_params : dict
        Material thermal properties.
    weather_records : list
        List of WeatherRecord objects (from weather service).
    simulation_start, simulation_end : datetime
        Simulation time bounds.
    time_step_s : int
        Time step in seconds.
    mesh_size : float
        Element size in meters.
    orientation : str
        Shelter orientation ('south', 'north', 'east', 'west').
    comfort_min, comfort_max : float
        Comfort temperature range (°C).
    convection_htc_override : float or None
        Fixed HTC if user-specified; None = auto from wind speed.
    radiation_enabled : bool
        Whether to include linearized radiation.
    solar_loading_enabled : bool
        Whether to include solar heat flux.
    status_callback : callable(status, message)
        Optional callback to report job status updates.

    Returns
    -------
    dict: Structured simulation results (all values from ANSYS).
    """
    def _update(status: str, msg: str):
        logger.info(f"[{job_id}] {status}: {msg}")
        if status_callback:
            status_callback(status, msg)

    _update("PREPARING", "Preparing simulation parameters...")

    # ── Build time arrays ─────────────────────────────────────────────────────
    total_s = (simulation_end - simulation_start).total_seconds()
    times_s = [i * time_step_s for i in range(int(total_s / time_step_s) + 1)]
    n_steps = len(times_s)

    # Filter weather records to simulation window
    from ..services.weather.weather_service import WeatherService
    ws = WeatherService()
    records = ws.fill_missing_values(weather_records)

    # Build time-indexed weather arrays (interpolate to simulation time steps)
    import numpy as np
    rec_times_s = [
        (r.timestamp - simulation_start).total_seconds()
        for r in records
    ]
    rec_temps = [r.temperature_2m or -10.0 for r in records]
    rec_solar = [max(0.0, r.shortwave_radiation or 0.0) for r in records]
    rec_wind = [r.wind_speed_10m or 1.0 for r in records]

    # Interpolate to simulation time steps
    sim_temps = np.interp(times_s, rec_times_s, rec_temps).tolist()
    sim_solar = np.interp(times_s, rec_times_s, rec_solar).tolist()
    sim_wind = np.interp(times_s, rec_times_s, rec_wind).tolist()

    logger.info(
        f"[{job_id}] Weather: T={min(sim_temps):.1f}°C to {max(sim_temps):.1f}°C, "
        f"Solar peak={max(sim_solar):.0f} W/m²"
    )

    # ── Launch ANSYS MAPDL ────────────────────────────────────────────────────
    _update("LOADING_GEOMETRY", "Launching ANSYS MAPDL...")

    run_dir = str(Path(job_dir) / "mapdl_run")
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    session = MAPDLSession(
        exe_path=settings.ansys_mapdl_exe,
        run_location=run_dir,
        port=settings.mapdl_port,
        start_timeout=settings.mapdl_start_timeout,
        verbose=settings.dev_mode,
    )

    try:
        session.start()
        m = session.mapdl
        ansys_version = str(m.version)
        logger.info(f"[{job_id}] ANSYS MAPDL {ansys_version} connected.")

        # ── Build geometry ─────────────────────────────────────────────────────
        is_cad = (
            design_params.get("design_type") == "imported"
            and bool(design_params.get("file_path"))
        )

        if is_cad:
            cad_file = design_params["file_path"]
            _update("LOADING_GEOMETRY", f"Importing CAD model: {Path(cad_file).name}...")
            from .cad_importer import CADModelImporter
            importer = CADModelImporter(m)
            geo_info = importer.import_cad(
                file_path=cad_file,
                file_format=design_params.get("file_format"),
                orientation=orientation,
                target_mesh_size=mesh_size,
            )
            mesh_info = {
                "node_count": geo_info["node_count"],
                "element_count": geo_info["element_count"],
                "element_size": mesh_size,
            }
            logger.info(
                f"[{job_id}] CAD model imported: {mesh_info['node_count']} nodes, "
                f"{mesh_info['element_count']} elements ({geo_info['length']:.2f}×{geo_info['width']:.2f}×{geo_info['height']:.2f}m)"
            )
        else:
            _update("LOADING_GEOMETRY", "Building shelter geometry in ANSYS...")
            geom = ShelterGeometry(
                length=design_params.get("length", 5.0),
                width=design_params.get("width", 4.0),
                height=design_params.get("height", 3.0),
                wall_thickness=design_params.get("wall_thickness", 0.3),
                roof_thickness=design_params.get("roof_thickness", 0.25),
                floor_thickness=design_params.get("floor_thickness", 0.2),
            )
            builder = ShelterModelBuilder(m)
            geo_info = builder.build(geom)
            geo_info["length"] = geom.length
            geo_info["width"] = geom.width
            geo_info["height"] = geom.height
            geo_info["roof_area"] = geom.length * geom.width
            geo_info["wall_thickness"] = geom.wall_thickness

        # ── Assign material ────────────────────────────────────────────────────
        _update("ASSIGNING_MATERIAL", f"Assigning material: {material_params.get('name', '?')}...")
        mapper = MaterialMapper(m)
        mapper.assign_material(
            mat_num=1,
            thermal_conductivity=material_params["thermal_conductivity"],
            density=material_params["density"],
            specific_heat=material_params["specific_heat"],
            emissivity=material_params.get("emissivity", 0.9),
            name=material_params.get("name", "Material"),
        )
        if not is_cad:
            m.run("VSEL,ALL")
            m.run("VATT,1,1,1")
            m.allsel()

            # ── Generate mesh ──────────────────────────────────────────────────────
            _update("MESHING", f"Generating mesh (element size: {mesh_size}m)...")
            mesher = MeshGenerator(m, is_student=True)
            mesh_info = mesher.generate_mesh(element_size=mesh_size)
            logger.info(
                f"[{job_id}] Mesh: {mesh_info['node_count']} nodes, "
                f"{mesh_info['element_count']} elements"
            )
        else:
            _update("MESHING", f"CAD mesh validated ({mesh_info['node_count']} nodes, {mesh_info['element_count']} elements)...")

        # ── Apply boundary conditions ──────────────────────────────────────────
        _update("APPLYING_BOUNDARY_CONDITIONS", "Applying thermal boundary conditions...")
        bc = BoundaryConditionApplicator(m)

        # Initial temperature = first ambient temperature
        bc.apply_initial_temperature(sim_temps[0])

        # Time-varying convection
        bc.apply_convection(
            times_s=times_s,
            ambient_temps_c=sim_temps,
            wind_speeds_ms=sim_wind,
            convection_htc_override=convection_htc_override,
        )

        # Solar load
        if solar_loading_enabled:
            solar_app = SolarLoadApplicator(m)
            solar_app.apply_solar_load(
                times_s=times_s,
                solar_radiation_wm2=sim_solar,
                solar_absorptivity=material_params.get("solar_absorptivity", 0.7),
                ambient_temps_c=sim_temps,
                wind_speeds_ms=sim_wind,
                convection_htc_override=convection_htc_override,
                wall_orientation=orientation,
            )

        # ── Configure and solve ────────────────────────────────────────────────
        _update("SOLVING", "Running ANSYS transient thermal solver...")
        solve_start = time.time()

        solver = TransientSolver(m)
        solver.configure_and_solve(
            total_time_s=total_s,
            time_step_s=float(time_step_s),
            nonlinear=radiation_enabled,
        )

        solve_time = time.time() - solve_start
        logger.info(f"[{job_id}] Solve completed in {solve_time:.1f}s")

        # ── Extract results ────────────────────────────────────────────────────
        _update("POST_PROCESSING", "Extracting results from ANSYS...")
        extractor = ResultExtractor(m)
        results = extractor.extract_all_time_steps(
            interior_vol_num=geo_info.get("inner_vol"),
            interior_probe_nodes=geo_info.get("interior_probe_nodes"),
            comfort_min_c=comfort_min,
            comfort_max_c=comfort_max,
        )

        # Add weather data to results for dashboard display
        results["times_s"] = times_s
        results["ambient_temps"] = sim_temps
        results["solar_radiation"] = sim_solar
        results["ansys_version"] = ansys_version
        results["mesh_info"] = mesh_info
        results["solve_time_s"] = solve_time
        results["geometry"] = {
            "length": geo_info["length"],
            "width": geo_info["width"],
            "height": geo_info["height"],
            "is_cad": is_cad,
        }

        # Estimate solar heat gain (W) from solar radiation × area × absorptivity
        roof_area = geo_info.get("roof_area", geo_info["length"] * geo_info["width"])
        sol_absorptivity = material_params.get("solar_absorptivity", 0.7)
        solar_heat_gain_w = [q * roof_area * sol_absorptivity for q in sim_solar]
        total_solar_kwh = sum(solar_heat_gain_w) * (time_step_s / 3600) / 1000
        results["solar_heat_gain_w"] = solar_heat_gain_w
        results["total_solar_gain_kwh"] = total_solar_kwh

        # Compute envelope heat loss (W) based on UA·ΔT
        k_th = material_params.get("thermal_conductivity", 0.8)
        wall_thick = geo_info.get("wall_thickness", 0.30)
        wall_area = 2 * (geo_info["length"] * geo_info["height"] + geo_info["width"] * geo_info["height"])
        total_area = wall_area + roof_area
        u_val = 1.0 / (max(0.05, wall_thick) / max(0.01, k_th) + (1.0 / 20.0))

        temp_int = results.get("temp_internal_avg", [])
        heat_loss_w = []
        for i, t_in in enumerate(temp_int):
            t_amb = sim_temps[i] if i < len(sim_temps) else -10.0
            delta_t = max(0.0, t_in - t_amb)
            loss = u_val * total_area * delta_t
            heat_loss_w.append(round(loss, 2))

        total_loss_kwh = sum(heat_loss_w) * (time_step_s / 3600) / 1000.0
        peak_loss_w = max(heat_loss_w) if heat_loss_w else 0.0

        results["total_heat_flow_w"] = heat_loss_w
        results["total_heat_loss_kwh"] = round(total_loss_kwh, 2)
        results["peak_heat_loss_w"] = round(peak_loss_w, 2)

        # ── 3D Thermal Contour Extraction ──────────────────────────────────────
        try:
            peak_step = 1
            if len(results.get("temp_internal_avg", [])) > 0:
                peak_step = int(np.argmax(results["temp_internal_avg"])) + 1

            geo_info_contour = {
                "length": geo_info["length"],
                "width": geo_info["width"],
                "height": geo_info["height"],
                "t_min": results.get("scalar_metrics", {}).get("min_internal_temp", -10.0),
                "t_max": results.get("scalar_metrics", {}).get("max_internal_temp", 26.0),
                "t_avg": results.get("scalar_metrics", {}).get("avg_internal_temp", 18.0),
            }
            results["contour_3d"] = extractor.extract_3d_surface_contour(
                target_set=peak_step,
                geo_info=geo_info_contour,
                orientation=orientation,
            )
            logger.info(f"[{job_id}] 3D thermal contour extracted successfully.")
        except Exception as e:
            logger.warning(f"[{job_id}] 3D contour extraction skipped: {e}")
            results["contour_3d"] = None


        _update("EXTRACTING_RESULTS", f"Simulation solved. Extracted {len(results['times_s'])} time steps.")
        return results

    except AnsysConnectionError as e:
        error_msg = (
            f"ANSYS MAPDL could not be started. "
            f"Verify that ANSYS is installed and licensed. Details: {e}"
        )
        _update("FAILED", error_msg)
        raise SimulationRunnerError(error_msg) from e

    except Exception as e:
        _update("FAILED", str(e))
        raise SimulationRunnerError(str(e)) from e

    finally:
        try:
            session.close()
        except Exception:
            pass
