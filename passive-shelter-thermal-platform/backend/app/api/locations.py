"""
FastAPI router for location and weather data management.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database.base import get_db
from ..database.models import Location, WeatherDataset
from ..schemas.schemas import (
    LocationQuery, LocationResponse, WeatherRequest,
    WeatherDatasetResponse, WeatherDataPoint, WeatherValidationResult,
)
from ..services.geocoding.geocoding_service import GeocodingService
from ..services.weather.weather_service import WeatherService

router = APIRouter(prefix="/api/v1", tags=["Location & Weather"])
_geocoding = GeocodingService()
_weather = WeatherService()


@router.post("/locations/search", response_model=LocationResponse)
async def search_location(query: LocationQuery, db: Session = Depends(get_db)):
    """Geocode a human-readable location string."""
    result = await _geocoding.geocode(query.query)
    if not result:
        raise HTTPException(status_code=404, detail=f"Location not found: '{query.query}'")

    # Check if already stored
    existing = db.query(Location).filter(
        Location.name == result.name,
        Location.latitude.between(result.latitude - 0.01, result.latitude + 0.01),
    ).first()

    if existing:
        return existing

    # Store new location
    loc = Location(
        id=str(uuid.uuid4()),
        name=result.name,
        display_name=result.display_name,
        latitude=result.latitude,
        longitude=result.longitude,
        elevation=result.elevation,
        timezone=result.timezone,
        country=result.country,
        region=result.region,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@router.get("/locations", response_model=List[LocationResponse])
def list_locations(db: Session = Depends(get_db)):
    """List all saved locations."""
    return db.query(Location).order_by(Location.created_at.desc()).all()


@router.get("/locations/{location_id}", response_model=LocationResponse)
def get_location(location_id: str, db: Session = Depends(get_db)):
    """Get a specific location by ID."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc


@router.post("/weather/fetch", response_model=WeatherDatasetResponse)
async def fetch_weather(request: WeatherRequest, db: Session = Depends(get_db)):
    """Fetch and store weather data for a location."""
    loc = db.query(Location).filter(Location.id == request.location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    # Check cache
    if not request.force_refresh:
        start_dt = datetime.fromisoformat(request.start_date)
        end_dt = datetime.fromisoformat(request.end_date)
        cached = db.query(WeatherDataset).filter(
            WeatherDataset.location_id == request.location_id,
            WeatherDataset.start_datetime <= start_dt,
            WeatherDataset.end_datetime >= end_dt,
        ).first()
        if cached:
            records = _weather.from_json_records(cached.data_json or [])
            return _build_weather_response(cached, records)

    # Fetch from API
    try:
        dataset = await _weather.fetch_weather(
            latitude=loc.latitude,
            longitude=loc.longitude,
            start_date=request.start_date,
            end_date=request.end_date,
            location_name=loc.name,
            elevation=loc.elevation,
            timezone=loc.timezone or "auto",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {e}")

    # Validate
    is_valid, errors, warnings = _weather.validate_dataset(dataset)
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail={"message": "Weather data validation failed", "errors": errors, "warnings": warnings},
        )

    # Store
    data_json = _weather.to_json_serializable(dataset)
    wd = WeatherDataset(
        id=str(uuid.uuid4()),
        location_id=loc.id,
        provider=dataset.provider,
        start_datetime=dataset.start_datetime,
        end_datetime=dataset.end_datetime,
        resolution_hours=request.resolution_hours,
        data_json=data_json,
    )
    db.add(wd)
    db.commit()
    db.refresh(wd)

    return _build_weather_response(wd, dataset.records)


@router.get("/weather/{dataset_id}", response_model=WeatherDatasetResponse)
def get_weather_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Get a stored weather dataset."""
    wd = db.query(WeatherDataset).filter(WeatherDataset.id == dataset_id).first()
    if not wd:
        raise HTTPException(status_code=404, detail="Weather dataset not found")
    records = _weather.from_json_records(wd.data_json or [])
    return _build_weather_response(wd, records)


@router.post("/weather/validate/{dataset_id}", response_model=WeatherValidationResult)
def validate_weather(dataset_id: str, db: Session = Depends(get_db)):
    """Validate a stored weather dataset."""
    wd = db.query(WeatherDataset).filter(WeatherDataset.id == dataset_id).first()
    if not wd:
        raise HTTPException(status_code=404, detail="Weather dataset not found")
    records = _weather.from_json_records(wd.data_json or [])

    class _FakeDataset:
        pass
    ds = _FakeDataset()
    ds.records = records

    is_valid, errors, warnings = _weather.validate_dataset(ds)

    missing = {}
    for r in records:
        for field in ["temperature_2m", "shortwave_radiation", "wind_speed_10m"]:
            if getattr(r, field, None) is None:
                missing[field] = missing.get(field, 0) + 1

    return WeatherValidationResult(
        is_valid=is_valid,
        warnings=warnings,
        errors=errors,
        data_points=len(records),
        missing_values=missing,
    )


def _build_weather_response(wd: WeatherDataset, records) -> WeatherDatasetResponse:
    points = []
    for r in records:
        points.append(WeatherDataPoint(
            timestamp=r.timestamp.isoformat() if hasattr(r, "timestamp") else str(r.get("timestamp", "")),
            temperature_2m=getattr(r, "temperature_2m", None) or r.get("temperature_2m") if isinstance(r, dict) else r.temperature_2m,
            relative_humidity_2m=getattr(r, "relative_humidity_2m", None) if not isinstance(r, dict) else r.get("relative_humidity_2m"),
            wind_speed_10m=getattr(r, "wind_speed_10m", None) if not isinstance(r, dict) else r.get("wind_speed_10m"),
            wind_direction_10m=getattr(r, "wind_direction_10m", None) if not isinstance(r, dict) else r.get("wind_direction_10m"),
            cloud_cover=getattr(r, "cloud_cover", None) if not isinstance(r, dict) else r.get("cloud_cover"),
            precipitation=getattr(r, "precipitation", None) if not isinstance(r, dict) else r.get("precipitation"),
            shortwave_radiation=getattr(r, "shortwave_radiation", None) if not isinstance(r, dict) else r.get("shortwave_radiation"),
            direct_radiation=getattr(r, "direct_radiation", None) if not isinstance(r, dict) else r.get("direct_radiation"),
            diffuse_radiation=getattr(r, "diffuse_radiation", None) if not isinstance(r, dict) else r.get("diffuse_radiation"),
            surface_pressure=getattr(r, "surface_pressure", None) if not isinstance(r, dict) else r.get("surface_pressure"),
        ))
    return WeatherDatasetResponse(
        id=wd.id,
        location_id=wd.location_id,
        provider=wd.provider,
        start_datetime=wd.start_datetime,
        end_datetime=wd.end_datetime,
        resolution_hours=wd.resolution_hours,
        data=points,
        fetched_at=wd.fetched_at,
    )
