"""
Weather service: orchestrates provider selection, caching, and validation.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional, Tuple

from .base_provider import WeatherRecord, WeatherDataset
from .open_meteo_provider import OpenMeteoProvider


class WeatherValidationError(Exception):
    pass


class WeatherService:
    """
    High-level weather service.
    - Selects the appropriate provider.
    - Validates retrieved data.
    - Normalizes for ANSYS boundary condition preparation.
    """

    def __init__(self):
        self._providers = {
            "open-meteo": OpenMeteoProvider(),
        }
        self._default_provider = "open-meteo"

    def get_provider(self, name: str = None):
        name = name or self._default_provider
        if name not in self._providers:
            raise ValueError(f"Unknown weather provider: {name}. Available: {list(self._providers.keys())}")
        return self._providers[name]

    async def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        location_name: str = "Unknown",
        elevation: Optional[float] = None,
        timezone: str = "auto",
        provider: str = None,
    ) -> WeatherDataset:
        """Fetch and validate weather data."""
        prov = self.get_provider(provider)
        dataset = await prov.fetch(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            location_name=location_name,
            elevation=elevation,
            timezone=timezone,
        )
        return dataset

    def validate_dataset(self, dataset: WeatherDataset) -> Tuple[bool, List[str], List[str]]:
        """
        Validate weather dataset before sending to ANSYS.

        Returns
        -------
        (is_valid, errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not dataset.records:
            errors.append("Weather dataset contains no records.")
            return False, errors, warnings

        records = dataset.records
        n = len(records)

        # Check for consecutive timestamps
        for i in range(1, n):
            prev = records[i - 1].timestamp
            curr = records[i].timestamp
            delta_h = (curr - prev).total_seconds() / 3600
            if delta_h <= 0:
                errors.append(f"Non-monotonic timestamp at index {i}: {curr}")
            elif delta_h > 2.0:
                warnings.append(f"Gap of {delta_h:.1f}h found before {curr}")

        # Count missing critical values
        missing_temp = sum(1 for r in records if r.temperature_2m is None)
        missing_solar = sum(1 for r in records if r.shortwave_radiation is None)
        missing_wind = sum(1 for r in records if r.wind_speed_10m is None)

        if missing_temp > n * 0.10:
            errors.append(f"Too many missing temperature values: {missing_temp}/{n}")
        elif missing_temp > 0:
            warnings.append(f"{missing_temp} missing temperature values (will be interpolated)")

        if missing_solar > n * 0.10:
            warnings.append(f"{missing_solar}/{n} missing solar radiation values")

        if missing_wind > n * 0.20:
            warnings.append(f"{missing_wind}/{n} missing wind speed values (will use defaults)")

        # Check for physically impossible values
        for i, r in enumerate(records):
            if r.temperature_2m is not None:
                if r.temperature_2m < -90 or r.temperature_2m > 60:
                    errors.append(f"Impossible temperature at index {i}: {r.temperature_2m}°C")
            if r.shortwave_radiation is not None:
                if r.shortwave_radiation < 0:
                    errors.append(f"Negative solar radiation at index {i}: {r.shortwave_radiation} W/m²")
                elif r.shortwave_radiation > 1500:
                    warnings.append(f"Unusually high solar radiation at index {i}: {r.shortwave_radiation} W/m²")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def fill_missing_values(self, records: List[WeatherRecord]) -> List[WeatherRecord]:
        """
        Fill missing values via linear interpolation.
        Used before constructing ANSYS boundary conditions.
        """
        import numpy as np

        def _interpolate(values: list) -> list:
            arr = np.array([v if v is not None else np.nan for v in values], dtype=float)
            nans = np.isnan(arr)
            if not nans.any():
                return values
            indices = np.arange(len(arr))
            valid = ~nans
            if valid.sum() < 2:
                # Fill with mean or 0
                fill_val = float(np.nanmean(arr)) if valid.any() else 0.0
                arr[nans] = fill_val
            else:
                arr[nans] = np.interp(indices[nans], indices[valid], arr[valid])
            return [float(v) for v in arr]

        # Extract and interpolate each field
        temps = _interpolate([r.temperature_2m for r in records])
        solar = _interpolate([max(0.0, r.shortwave_radiation or 0) for r in records])
        wind = _interpolate([r.wind_speed_10m if r.wind_speed_10m is not None else 1.0 for r in records])

        filled = []
        for i, r in enumerate(records):
            import copy
            nr = copy.copy(r)
            nr.temperature_2m = temps[i]
            nr.shortwave_radiation = solar[i]
            nr.wind_speed_10m = wind[i]
            filled.append(nr)

        return filled

    def to_json_serializable(self, dataset: WeatherDataset) -> list:
        """Convert WeatherDataset records to JSON-serializable list of dicts."""
        result = []
        for r in dataset.records:
            result.append({
                "timestamp": r.timestamp.isoformat(),
                "temperature_2m": r.temperature_2m,
                "relative_humidity_2m": r.relative_humidity_2m,
                "wind_speed_10m": r.wind_speed_10m,
                "wind_direction_10m": r.wind_direction_10m,
                "cloud_cover": r.cloud_cover,
                "precipitation": r.precipitation,
                "shortwave_radiation": r.shortwave_radiation,
                "direct_radiation": r.direct_radiation,
                "diffuse_radiation": r.diffuse_radiation,
                "surface_pressure": r.surface_pressure,
            })
        return result

    def from_json_records(self, data: list) -> List[WeatherRecord]:
        """Reconstruct WeatherRecord list from stored JSON data."""
        records = []
        for d in data:
            ts = datetime.fromisoformat(d["timestamp"])
            records.append(WeatherRecord(
                timestamp=ts,
                temperature_2m=d.get("temperature_2m"),
                relative_humidity_2m=d.get("relative_humidity_2m"),
                wind_speed_10m=d.get("wind_speed_10m"),
                wind_direction_10m=d.get("wind_direction_10m"),
                cloud_cover=d.get("cloud_cover"),
                precipitation=d.get("precipitation"),
                shortwave_radiation=d.get("shortwave_radiation"),
                direct_radiation=d.get("direct_radiation"),
                diffuse_radiation=d.get("diffuse_radiation"),
                surface_pressure=d.get("surface_pressure"),
            ))
        return records
