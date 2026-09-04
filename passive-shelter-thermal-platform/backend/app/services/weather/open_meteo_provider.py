"""
Open-Meteo weather provider.
Uses the Open-Meteo API (no API key required).
Retrieves hourly weather and solar radiation data.

API documentation: https://open-meteo.com/en/docs
"""
from __future__ import annotations

import httpx
from datetime import datetime, timezone
from typing import List, Optional
from .base_provider import BaseWeatherProvider, WeatherRecord, WeatherDataset


# Variables requested from Open-Meteo hourly endpoint.
# Clearly labeled as API-provided raw values (not derived).
OPEN_METEO_HOURLY_VARS = [
    "temperature_2m",           # API-provided: air temperature at 2m height (°C)
    "relative_humidity_2m",     # API-provided: relative humidity at 2m (%)
    "wind_speed_10m",           # API-provided: wind speed at 10m (m/s)
    "wind_direction_10m",       # API-provided: wind direction at 10m (degrees)
    "cloud_cover",              # API-provided: total cloud cover (%)
    "precipitation",            # API-provided: precipitation (mm)
    "shortwave_radiation",      # API-provided: global horizontal irradiance (W/m²)
    "direct_radiation",         # API-provided: direct (beam) horizontal irradiance (W/m²)
    "diffuse_radiation",        # API-provided: diffuse horizontal irradiance (W/m²)
    "surface_pressure",         # API-provided: surface pressure (hPa)
]


class OpenMeteoProvider(BaseWeatherProvider):
    """
    Weather provider using the Open-Meteo free API.
    No API key required. Data is sourced from ERA5/ECMWF reanalysis
    and numerical weather prediction models.

    IMPORTANT: The values provided are from the API as-is. They are
    NOT derived by this application. The application prepares these
    values as boundary conditions for ANSYS — the actual thermal
    simulation is performed by ANSYS, not this class.
    """

    BASE_URL = "https://api.open-meteo.com/v1"

    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "open-meteo"

    async def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        resolution_hours: float = 1.0,
        location_name: str = "Unknown",
        elevation: Optional[float] = None,
        timezone: str = "auto",
    ) -> WeatherDataset:
        """
        Fetch hourly weather data from Open-Meteo.

        Parameters
        ----------
        latitude, longitude : float
        start_date, end_date : str  YYYY-MM-DD
        resolution_hours : float    1.0 (hourly is native resolution)
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(OPEN_METEO_HOURLY_VARS),
            "timezone": timezone,
            "wind_speed_unit": "ms",   # metres per second
        }
        # Determine whether to use archive API (for historical dates) or forecast API
        is_historical = False
        try:
            req_end = datetime.fromisoformat(end_date)
            # If end date is more than 5 days in the past, use archive API
            if (datetime.utcnow() - req_end).total_seconds() > 5 * 86400:
                is_historical = True
        except Exception:
            pass

        url = "https://archive-api.open-meteo.com/v1/archive" if is_historical else f"{self.BASE_URL}/forecast"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params)
            # If forecast fails due to past dates, try archive endpoint as fallback
            if resp.status_code == 400 and not is_historical:
                resp = await client.get("https://archive-api.open-meteo.com/v1/archive", params=params)
            resp.raise_for_status()
            raw = resp.json()

        records = self._parse_response(raw)

        # Determine actual elevation from API response if not provided
        api_elevation = raw.get("elevation", elevation)
        api_timezone = raw.get("timezone", timezone)

        # Parse actual time bounds
        if records:
            start_dt = records[0].timestamp
            end_dt = records[-1].timestamp
        else:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)

        return WeatherDataset(
            provider=self.provider_name,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            elevation=api_elevation,
            timezone=api_timezone,
            start_datetime=start_dt,
            end_datetime=end_dt,
            resolution_hours=resolution_hours,
            records=records,
        )

    def _parse_response(self, raw: dict) -> List[WeatherRecord]:
        """Parse Open-Meteo API response into normalized WeatherRecords."""
        hourly = raw.get("hourly", {})
        timestamps = hourly.get("time", [])
        if not timestamps:
            return []

        def _get(key: str, idx: int) -> Optional[float]:
            vals = hourly.get(key, [])
            if idx < len(vals) and vals[idx] is not None:
                return float(vals[idx])
            return None

        records: List[WeatherRecord] = []
        for i, ts_str in enumerate(timestamps):
            # Open-Meteo returns ISO 8601 without timezone; assume UTC or local
            try:
                ts = datetime.fromisoformat(ts_str)
            except ValueError:
                continue

            record = WeatherRecord(
                timestamp=ts,
                temperature_2m=_get("temperature_2m", i),
                relative_humidity_2m=_get("relative_humidity_2m", i),
                wind_speed_10m=_get("wind_speed_10m", i),
                wind_direction_10m=_get("wind_direction_10m", i),
                cloud_cover=_get("cloud_cover", i),
                precipitation=_get("precipitation", i),
                shortwave_radiation=_get("shortwave_radiation", i),
                direct_radiation=_get("direct_radiation", i),
                diffuse_radiation=_get("diffuse_radiation", i),
                surface_pressure=_get("surface_pressure", i),
            )
            records.append(record)

        return records
