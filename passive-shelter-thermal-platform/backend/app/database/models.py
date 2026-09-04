"""
SQLAlchemy ORM models for the Passive Thermal Shelter Platform.
All tables are defined here for clarity and maintainability.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text, DateTime,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from .base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ─── Enums ────────────────────────────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    LOADING_GEOMETRY = "LOADING_GEOMETRY"
    ASSIGNING_MATERIAL = "ASSIGNING_MATERIAL"
    MESHING = "MESHING"
    APPLYING_BOUNDARY_CONDITIONS = "APPLYING_BOUNDARY_CONDITIONS"
    SOLVING = "SOLVING"
    POST_PROCESSING = "POST_PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MaterialCategory(str, enum.Enum):
    STRUCTURAL = "structural"
    INSULATION = "insulation"
    GLAZING = "glazing"
    THERMAL_MASS = "thermal_mass"
    PCM = "pcm"
    COMPOSITE = "composite"
    OTHER = "other"


# ─── Location ────────────────────────────────────────────────────────────────

class Location(Base):
    __tablename__ = "locations"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    display_name = Column(String)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float, nullable=True)
    timezone = Column(String, nullable=True)
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)

    weather_datasets = relationship("WeatherDataset", back_populates="location")


# ─── Weather ─────────────────────────────────────────────────────────────────

class WeatherDataset(Base):
    __tablename__ = "weather_datasets"

    id = Column(String, primary_key=True, default=_uuid)
    location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    provider = Column(String, default="open-meteo")
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    resolution_hours = Column(Float, default=1.0)
    data_json = Column(JSON, nullable=False)  # List of hourly records
    fetched_at = Column(DateTime, default=_now)
    is_cached = Column(Boolean, default=True)

    location = relationship("Location", back_populates="weather_datasets")


# ─── Material ────────────────────────────────────────────────────────────────

class Material(Base):
    __tablename__ = "materials"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, default=MaterialCategory.STRUCTURAL)
    description = Column(Text, nullable=True)

    # Thermal properties (SI units)
    thermal_conductivity = Column(Float, nullable=False)   # W/m·K
    density = Column(Float, nullable=False)                 # kg/m³
    specific_heat = Column(Float, nullable=False)           # J/kg·K
    emissivity = Column(Float, default=0.9)                 # dimensionless 0-1
    solar_absorptivity = Column(Float, default=0.7)         # dimensionless 0-1
    solar_reflectivity = Column(Float, default=0.3)         # dimensionless 0-1

    # Optional geometry reference
    default_thickness = Column(Float, nullable=True)        # m

    # Metadata
    notes = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    is_builtin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


# ─── Design ──────────────────────────────────────────────────────────────────

class Design(Base):
    __tablename__ = "designs"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    design_type = Column(String, default="parametric")  # 'parametric' | 'imported'

    # Geometry file (for imported designs)
    file_path = Column(String, nullable=True)
    file_format = Column(String, nullable=True)  # e.g. 'STEP', 'IGES'
    file_size_bytes = Column(Integer, nullable=True)

    # Parametric geometry (in meters)
    length = Column(Float, default=5.0)
    width = Column(Float, default=4.0)
    height = Column(Float, default=3.0)
    wall_thickness = Column(Float, default=0.3)
    roof_thickness = Column(Float, default=0.25)
    floor_thickness = Column(Float, default=0.2)

    # Derived
    floor_area = Column(Float, nullable=True)    # m²
    volume = Column(Float, nullable=True)        # m³

    # Openings
    window_area = Column(Float, default=1.5)     # m²
    door_area = Column(Float, default=2.0)       # m²
    window_orientation = Column(String, default="south")
    glazing_u_value = Column(Float, default=2.8)  # W/m²K

    # Default orientation
    orientation = Column(String, default="south")  # north/south/east/west or angle

    notes = Column(Text, nullable=True)
    is_builtin = Column(Boolean, default=False)
    thumbnail_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


# ─── Simulation Config ────────────────────────────────────────────────────────

class SimulationConfig(Base):
    __tablename__ = "simulation_configs"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=True)

    location_id = Column(String, ForeignKey("locations.id"), nullable=True)
    weather_dataset_id = Column(String, ForeignKey("weather_datasets.id"), nullable=True)

    # Timing
    simulation_start = Column(DateTime, nullable=False)
    simulation_end = Column(DateTime, nullable=False)
    time_step_seconds = Column(Integer, default=3600)

    # Physics
    mesh_size = Column(Float, default=0.3)          # m
    convection_coefficient = Column(Float, nullable=True)  # W/m²K (None = auto)
    radiation_enabled = Column(Boolean, default=True)
    solar_loading_enabled = Column(Boolean, default=True)
    thermal_mass_enabled = Column(Boolean, default=True)

    # Comfort
    comfort_min_temp = Column(Float, default=18.0)   # °C
    comfort_max_temp = Column(Float, default=27.0)   # °C

    # Occupants
    num_occupants = Column(Integer, default=0)
    heat_per_occupant = Column(Float, default=80.0)   # W

    # Recommendation weights (JSON)
    recommendation_weights = Column(JSON, default=lambda: {
        "comfort_compliance": 0.35,
        "nighttime_retention": 0.25,
        "heat_loss": 0.20,
        "solar_gain": 0.15,
        "temperature_stability": 0.05,
    })

    solver_settings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_now)

    jobs = relationship("SimulationJob", back_populates="config")


# ─── Simulation Job ───────────────────────────────────────────────────────────

class SimulationJob(Base):
    __tablename__ = "simulation_jobs"

    id = Column(String, primary_key=True, default=_uuid)
    sim_id = Column(String, unique=True, nullable=False)  # e.g. SIM-2026-0001
    config_id = Column(String, ForeignKey("simulation_configs.id"), nullable=False)
    design_id = Column(String, ForeignKey("designs.id"), nullable=False)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    orientation = Column(String, default="south")

    status = Column(String, default=JobStatus.QUEUED)
    progress_message = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    # ANSYS job directory
    ansys_job_dir = Column(String, nullable=True)
    ansys_version_used = Column(String, nullable=True)
    pymapdl_version_used = Column(String, nullable=True)

    # Timing
    created_at = Column(DateTime, default=_now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    config = relationship("SimulationConfig", back_populates="jobs")
    design = relationship("Design")
    material = relationship("Material")
    result = relationship("SimulationResult", back_populates="job", uselist=False)


# ─── Simulation Result ────────────────────────────────────────────────────────

class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("simulation_jobs.id"), unique=True, nullable=False)

    # Time-series data (JSON arrays)
    timestamps = Column(JSON, nullable=True)          # ISO strings
    temp_internal = Column(JSON, nullable=True)       # °C
    temp_ambient = Column(JSON, nullable=True)        # °C
    solar_radiation = Column(JSON, nullable=True)     # W/m²
    solar_heat_gain = Column(JSON, nullable=True)     # W
    heat_flux_external = Column(JSON, nullable=True)  # W/m²
    total_heat_flow = Column(JSON, nullable=True)     # W

    # Scalar metrics
    min_internal_temp = Column(Float, nullable=True)
    max_internal_temp = Column(Float, nullable=True)
    avg_internal_temp = Column(Float, nullable=True)
    nighttime_min_temp = Column(Float, nullable=True)
    nighttime_avg_temp = Column(Float, nullable=True)
    daytime_max_temp = Column(Float, nullable=True)

    comfort_hours = Column(Float, nullable=True)
    comfort_percentage = Column(Float, nullable=True)

    total_solar_gain_kwh = Column(Float, nullable=True)
    total_heat_loss_kwh = Column(Float, nullable=True)
    peak_heat_loss_w = Column(Float, nullable=True)
    temp_fluctuation_std = Column(Float, nullable=True)

    nighttime_retention_score = Column(Float, nullable=True)  # 0-100

    # ANSYS metadata
    node_count = Column(Integer, nullable=True)
    element_count = Column(Integer, nullable=True)
    solve_time_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime, default=_now)

    job = relationship("SimulationJob", back_populates="result")


# ─── Recommendation ──────────────────────────────────────────────────────────

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, nullable=False)
    recommended_job_id = Column(String, ForeignKey("simulation_jobs.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    weights_used = Column(JSON, nullable=False)
    scores_breakdown = Column(JSON, nullable=True)
    explanation = Column(JSON, nullable=True)
    all_scores = Column(JSON, nullable=True)  # {job_id: score}
    created_at = Column(DateTime, default=_now)

    recommended_job = relationship("SimulationJob")


# ─── Report ──────────────────────────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=_uuid)
    recommendation_id = Column(String, ForeignKey("recommendations.id"), nullable=True)
    session_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_now)

    recommendation = relationship("Recommendation")


# ─── AppSettings ─────────────────────────────────────────────────────────────

class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
