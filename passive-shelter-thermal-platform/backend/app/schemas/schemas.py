"""
Pydantic schemas for all API request/response models.
Separated from ORM models to maintain clean API contracts.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


# ─── Location ────────────────────────────────────────────────────────────────

class LocationQuery(BaseModel):
    query: str = Field(..., description="Human-readable location, e.g. 'Leh, Ladakh, India'")


class LocationResponse(BaseModel):
    id: Optional[str] = None
    name: str
    display_name: Optional[str] = None
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    timezone: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Weather ─────────────────────────────────────────────────────────────────

class WeatherRequest(BaseModel):
    location_id: str
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    resolution_hours: float = Field(default=1.0)
    force_refresh: bool = False


class WeatherDataPoint(BaseModel):
    timestamp: str
    temperature_2m: Optional[float] = None          # °C
    relative_humidity_2m: Optional[float] = None    # %
    wind_speed_10m: Optional[float] = None           # m/s
    wind_direction_10m: Optional[float] = None      # degrees
    cloud_cover: Optional[float] = None             # %
    precipitation: Optional[float] = None           # mm
    shortwave_radiation: Optional[float] = None     # W/m²
    direct_radiation: Optional[float] = None        # W/m²
    diffuse_radiation: Optional[float] = None       # W/m²
    surface_pressure: Optional[float] = None        # hPa


class WeatherDatasetResponse(BaseModel):
    id: str
    location_id: str
    provider: str
    start_datetime: datetime
    end_datetime: datetime
    resolution_hours: float
    data: List[WeatherDataPoint]
    fetched_at: datetime

    model_config = {"from_attributes": True}


class WeatherValidationResult(BaseModel):
    is_valid: bool
    warnings: List[str] = []
    errors: List[str] = []
    data_points: int
    missing_values: Dict[str, int] = {}


# ─── Material ────────────────────────────────────────────────────────────────

class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(default="structural")
    description: Optional[str] = None
    thermal_conductivity: float = Field(..., gt=0, description="W/m·K")
    density: float = Field(..., gt=0, description="kg/m³")
    specific_heat: float = Field(..., gt=0, description="J/kg·K")
    emissivity: float = Field(default=0.9, ge=0, le=1)
    solar_absorptivity: float = Field(default=0.7, ge=0, le=1)
    solar_reflectivity: float = Field(default=0.3, ge=0, le=1)
    default_thickness: Optional[float] = Field(default=None, gt=0, description="m")
    notes: Optional[str] = None
    source: Optional[str] = None


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    thermal_conductivity: Optional[float] = Field(default=None, gt=0)
    density: Optional[float] = Field(default=None, gt=0)
    specific_heat: Optional[float] = Field(default=None, gt=0)
    emissivity: Optional[float] = Field(default=None, ge=0, le=1)
    solar_absorptivity: Optional[float] = Field(default=None, ge=0, le=1)
    solar_reflectivity: Optional[float] = Field(default=None, ge=0, le=1)
    default_thickness: Optional[float] = Field(default=None, gt=0)
    notes: Optional[str] = None
    source: Optional[str] = None


class MaterialResponse(BaseModel):
    id: str
    name: str
    category: str
    description: Optional[str] = None
    thermal_conductivity: float
    density: float
    specific_heat: float
    emissivity: float
    solar_absorptivity: float
    solar_reflectivity: float
    default_thickness: Optional[float] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    is_builtin: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Design ──────────────────────────────────────────────────────────────────

class DesignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    design_type: str = Field(default="parametric")
    length: float = Field(default=5.0, gt=0, description="m")
    width: float = Field(default=4.0, gt=0, description="m")
    height: float = Field(default=3.0, gt=0, description="m")
    wall_thickness: float = Field(default=0.3, gt=0, description="m")
    roof_thickness: float = Field(default=0.25, gt=0, description="m")
    floor_thickness: float = Field(default=0.2, gt=0, description="m")
    window_area: float = Field(default=1.5, ge=0, description="m²")
    door_area: float = Field(default=2.0, ge=0, description="m²")
    window_orientation: str = Field(default="south")
    glazing_u_value: float = Field(default=2.8, gt=0, description="W/m²K")
    orientation: str = Field(default="south")
    notes: Optional[str] = None


class DesignResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    design_type: str
    file_path: Optional[str] = None
    file_format: Optional[str] = None
    length: float
    width: float
    height: float
    wall_thickness: float
    roof_thickness: float
    floor_thickness: float
    floor_area: Optional[float] = None
    volume: Optional[float] = None
    window_area: float
    door_area: float
    window_orientation: str
    glazing_u_value: float
    orientation: str
    notes: Optional[str] = None
    is_builtin: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Simulation ──────────────────────────────────────────────────────────────

class RecommendationWeights(BaseModel):
    comfort_compliance: float = Field(default=0.35, ge=0, le=1)
    nighttime_retention: float = Field(default=0.25, ge=0, le=1)
    heat_loss: float = Field(default=0.20, ge=0, le=1)
    solar_gain: float = Field(default=0.15, ge=0, le=1)
    temperature_stability: float = Field(default=0.05, ge=0, le=1)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "RecommendationWeights":
        total = (
            self.comfort_compliance + self.nighttime_retention +
            self.heat_loss + self.solar_gain + self.temperature_stability
        )
        if total <= 0:
            self.comfort_compliance = 0.35
            self.nighttime_retention = 0.25
            self.heat_loss = 0.20
            self.solar_gain = 0.15
            self.temperature_stability = 0.05
        elif abs(total - 1.0) > 1e-4:
            # Auto-normalize to 1.0 gracefully rather than throwing 422
            c = round(self.comfort_compliance / total, 4)
            n = round(self.nighttime_retention / total, 4)
            h = round(self.heat_loss / total, 4)
            s = round(self.solar_gain / total, 4)
            t = round(1.0 - (c + n + h + s), 4)
            self.comfort_compliance = max(0.0, c)
            self.nighttime_retention = max(0.0, n)
            self.heat_loss = max(0.0, h)
            self.solar_gain = max(0.0, s)
            self.temperature_stability = max(0.0, t)
        return self


class SimulationConfigCreate(BaseModel):
    name: Optional[str] = None
    location_id: str
    weather_dataset_id: str
    design_ids: List[str] = Field(..., min_length=1)
    material_ids: List[str] = Field(..., min_length=1)
    orientation: str = Field(default="south")
    simulation_start: datetime
    simulation_end: datetime
    time_step_seconds: int = Field(default=3600, ge=60, le=86400)
    mesh_size: float = Field(default=0.3, gt=0.05, le=2.0, description="m")
    convection_coefficient: Optional[float] = Field(default=None, gt=0)
    radiation_enabled: bool = True
    solar_loading_enabled: bool = True
    thermal_mass_enabled: bool = True
    comfort_min_temp: float = Field(default=18.0)
    comfort_max_temp: float = Field(default=27.0)
    num_occupants: int = Field(default=0, ge=0)
    heat_per_occupant: float = Field(default=80.0, ge=0)
    recommendation_weights: RecommendationWeights = Field(default_factory=RecommendationWeights)


class SimulationJobResponse(BaseModel):
    id: str
    sim_id: str
    config_id: str
    design_id: str
    material_id: str
    orientation: str
    status: str
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    ansys_job_dir: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobStatusUpdate(BaseModel):
    job_id: str
    status: str
    progress_message: Optional[str] = None
    error_message: Optional[str] = None


# ─── Results ─────────────────────────────────────────────────────────────────

class SimulationResultResponse(BaseModel):
    id: str
    job_id: str
    timestamps: Optional[List[str]] = None
    temp_internal: Optional[List[float]] = None
    temp_ambient: Optional[List[float]] = None
    solar_radiation: Optional[List[float]] = None
    solar_heat_gain: Optional[List[float]] = None
    heat_flux_external: Optional[List[float]] = None
    total_heat_flow: Optional[List[float]] = None
    min_internal_temp: Optional[float] = None
    max_internal_temp: Optional[float] = None
    avg_internal_temp: Optional[float] = None
    nighttime_min_temp: Optional[float] = None
    nighttime_avg_temp: Optional[float] = None
    daytime_max_temp: Optional[float] = None
    comfort_hours: Optional[float] = None
    comfort_percentage: Optional[float] = None
    total_solar_gain_kwh: Optional[float] = None
    total_heat_loss_kwh: Optional[float] = None
    peak_heat_loss_w: Optional[float] = None
    temp_fluctuation_std: Optional[float] = None
    nighttime_retention_score: Optional[float] = None
    node_count: Optional[int] = None
    element_count: Optional[int] = None
    solve_time_seconds: Optional[float] = None
    contour_3d: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Recommendation ──────────────────────────────────────────────────────────

class RecommendationResponse(BaseModel):
    id: str
    session_id: str
    recommended_job_id: str
    overall_score: float
    weights_used: Dict[str, float]
    scores_breakdown: Optional[Dict[str, float]] = None
    explanation: Optional[List[str]] = None
    all_scores: Optional[Dict[str, float]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── ANSYS Status ─────────────────────────────────────────────────────────────

class AnsysStatusResponse(BaseModel):
    ansys_detected: bool
    ansys_version: Optional[str] = None
    ansys_install_path: Optional[str] = None
    mapdl_exe_path: Optional[str] = None
    mapdl_exe_exists: bool = False
    pymapdl_version: Optional[str] = None
    pymapdl_available: bool = False
    connection_tested: bool = False
    connection_successful: Optional[bool] = None
    connection_error: Optional[str] = None
    student_license: bool = True
    node_limit: Optional[int] = None


class AnsysConfigRequest(BaseModel):
    exe_path: str = Field(..., description="Path to ansysXXX.exe or root installation directory")
    test_now: bool = Field(default=True, description="Whether to immediately test live MAPDL gRPC startup")


# ─── Report ──────────────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    session_id: str
    recommendation_id: str
    title: Optional[str] = Field(default="Passive Thermal Shelter Analysis Report")


class ReportResponse(BaseModel):
    id: str
    title: str
    file_path: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── WebSocket Messages ───────────────────────────────────────────────────────

class WSMessage(BaseModel):
    type: str  # "job_update" | "system" | "error"
    payload: Dict[str, Any]
