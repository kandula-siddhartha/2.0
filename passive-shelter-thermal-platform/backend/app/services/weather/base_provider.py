"""
Weather provider abstraction layer.
All weather providers normalize data into a common WeatherRecord format.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class WeatherRecord:
    """
    Normalized weather data record for a single time step.
    All providers must produce this format.
    """
    timestamp: datetime

    # Temperature (°C)
    temperature_2m: Optional[float] = None

    # Humidity (%)
    relative_humidity_2m: Optional[float] = None

    # Wind
    wind_speed_10m: Optional[float] = None    # m/s
    wind_direction_10m: Optional[float] = None  # degrees

    # Cloud/sky
    cloud_cover: Optional[float] = None       # %

    # Precipitation
    precipitation: Optional[float] = None     # mm

    # Solar radiation (W/m²) — API-provided values
    shortwave_radiation: Optional[float] = None   # GHI: global horizontal irradiance
    direct_radiation: Optional[float] = None      # DNI: direct normal / direct horizontal
    diffuse_radiation: Optional[float] = None     # DHI: diffuse horizontal irradiance

    # Pressure
    surface_pressure: Optional[float] = None  # hPa


@dataclass
class WeatherDataset:
    """Normalized weather dataset produced by a provider."""
    provider: str
    location_name: str
    latitude: float
    longitude: float
    elevation: Optional[float]
    timezone: str
    start_datetime: datetime
    end_datetime: datetime
    resolution_hours: float
    records: List[WeatherRecord] = field(default_factory=list)
    is_forecast: bool = False
    data_type: str = "historical"


class BaseWeatherProvider(ABC):
    """Abstract weather provider. Implement to add new providers."""

    @abstractmethod
    async def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        resolution_hours: float = 1.0,
    ) -> WeatherDataset:
        """
        Fetch weather data for the given location and time period.

        Parameters
        ----------
        latitude, longitude : float
            Location coordinates.
        start_date, end_date : str
            Date strings in YYYY-MM-DD format.
        resolution_hours : float
            Desired temporal resolution.

        Returns
        -------
        WeatherDataset
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...
