"""
Geocoding service using the Open-Meteo Geocoding API.
Converts human-readable location strings to lat/lon/elevation/timezone.
"""
from __future__ import annotations

import httpx
from typing import Optional
from dataclasses import dataclass


@dataclass
class GeocodingResult:
    name: str
    display_name: str
    latitude: float
    longitude: float
    elevation: Optional[float]
    timezone: Optional[str]
    country: Optional[str]
    region: Optional[str]
    country_code: Optional[str]


class GeocodingService:
    """
    Geocoding provider using the Open-Meteo Geocoding API.
    No API key required.
    """

    BASE_URL = "https://geocoding-api.open-meteo.com/v1"

    def __init__(self, timeout: float = 15.0):
        self._timeout = timeout

    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        """
        Geocode a location string.

        Parameters
        ----------
        query : str
            Human-readable location, e.g. "Leh, Ladakh, India"

        Returns
        -------
        GeocodingResult or None if not found.
        """
        params = {
            "name": query,
            "count": 5,
            "language": "en",
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self.BASE_URL}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return None

        # Pick the most relevant result (first by default)
        r = results[0]
        return GeocodingResult(
            name=r.get("name", query),
            display_name=self._build_display_name(r),
            latitude=float(r["latitude"]),
            longitude=float(r["longitude"]),
            elevation=r.get("elevation"),
            timezone=r.get("timezone"),
            country=r.get("country"),
            region=r.get("admin1"),
            country_code=r.get("country_code"),
        )

    @staticmethod
    def _build_display_name(r: dict) -> str:
        parts = [r.get("name", "")]
        if r.get("admin1"):
            parts.append(r["admin1"])
        if r.get("country"):
            parts.append(r["country"])
        return ", ".join(p for p in parts if p)
