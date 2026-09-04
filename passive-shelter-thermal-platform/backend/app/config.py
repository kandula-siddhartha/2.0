"""
Application configuration using pydantic-settings.
Reads from .env file and environment variables.
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DATA_DIR / "shelter_thermal.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── ANSYS ─────────────────────────────────────────────────────────────────
    ansys_install_path: str = Field(
        default=r"D:\ANSYS\ANSYS Inc\ANSYS Student\v261",
        description="Root directory of the ANSYS installation",
    )
    ansys_version: int = Field(default=261, description="ANSYS version number (e.g. 261 for v26.1)")
    ansys_mapdl_exe: str = Field(
        default=r"D:\ANSYS\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ansys261.exe",
        description="Full path to the MAPDL executable",
    )
    mapdl_port: int = Field(default=50052, description="gRPC port for PyMAPDL communication")
    mapdl_start_timeout: int = Field(default=120, description="Seconds to wait for MAPDL to start")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default=f"sqlite:///{_DB_PATH.as_posix()}",
        description="SQLAlchemy database URL",
    )

    @property
    def resolved_database_url(self) -> str:
        if self.database_url.startswith("sqlite:///.") or self.database_url == "sqlite:///./data/shelter_thermal.db":
            return f"sqlite:///{_DB_PATH.as_posix()}"
        return self.database_url

    # ── Data directories ──────────────────────────────────────────────────────
    data_dir: str = Field(default=str(_DATA_DIR))
    simulations_dir: str = Field(default=str(_DATA_DIR / "simulations"))
    reports_dir: str = Field(default=str(_DATA_DIR / "reports"))
    designs_dir: str = Field(default=str(_DATA_DIR / "designs"))

    # ── Weather APIs ──────────────────────────────────────────────────────────
    weather_api_base_url: str = Field(default="https://api.open-meteo.com/v1")
    geocoding_api_base_url: str = Field(default="https://geocoding-api.open-meteo.com/v1")

    # ── App ───────────────────────────────────────────────────────────────────
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    frontend_url: str = Field(default="http://localhost:5173")
    log_level: str = Field(default="INFO")

    # ── Simulation defaults ───────────────────────────────────────────────────
    max_concurrent_simulations: int = Field(default=1)
    default_time_step_seconds: int = Field(default=3600)
    default_simulation_hours: int = Field(default=24)
    default_mesh_size: float = Field(default=0.1)

    # ── Comfort range ─────────────────────────────────────────────────────────
    default_comfort_min: float = Field(default=18.0)
    default_comfort_max: float = Field(default=27.0)

    # ── Dev ───────────────────────────────────────────────────────────────────
    dev_mode: bool = Field(default=False)

    def ensure_directories(self) -> None:
        """Create required data directories if they don't exist."""
        for d in [self.data_dir, self.simulations_dir, self.reports_dir, self.designs_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()
settings.ensure_directories()
