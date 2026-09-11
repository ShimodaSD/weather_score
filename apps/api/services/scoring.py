"""Weather retrieval and activity scoring orchestration."""

import asyncio
import math
from numbers import Real

import requests
from fastapi import HTTPException, status
from weather_score.application.main import (
    calculate_activity_score,
    calculate_activity_score_by_training_type,
)
from weather_score.application.run_grade import RunGrade, calculate_run_grade
from weather_score.weather.providers.openmeteo import fetch_elevation
from weather_score.weather.providers.weather_api import fetch_current_weather

try:
    from ..schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from ..schemas.score import TrainingRunType
    from .geocoding import geocode_address
except ImportError:
    from schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from schemas.score import TrainingRunType
    from services.geocoding import geocode_address


async def score_activity_at_address(
    address: str,
    training_type: TrainingRunType | None = None,
    coordinates: CoordinatesResponse | None = None,
) -> float | ErrorResponse | LocationOptionsResponse:
    """Fetch conditions for an address and calculate its activity score."""
    coordinates = coordinates or await geocode_address(address)
    if coordinates is None:
        return ErrorResponse(
            error="Could not retrieve latitude and longitude for the given address."
        )
    if isinstance(coordinates, LocationOptionsResponse):
        return coordinates

    latitude = coordinates.latitude.strip()
    longitude = coordinates.longitude.strip()
    try:
        weather, altitude = await asyncio.gather(
            fetch_current_weather(latitude, longitude),
            fetch_elevation(latitude, longitude),
        )
        if training_type is not None:
            return await calculate_activity_score_by_training_type(
                weather, altitude, training_type
            )
        return await calculate_activity_score(weather, altitude)
    except (requests.RequestException, TimeoutError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve weather data.",
        ) from error


async def grade_run_at_address(
    address: str,
    average_pace_minutes_per_km: float,
) -> RunGrade | ErrorResponse | LocationOptionsResponse:
    """Fetch current conditions for an address and grade a running pace."""
    coordinates = await geocode_address(address)
    if coordinates is None:
        return ErrorResponse(
            error="Could not retrieve latitude and longitude for the given address."
        )
    if isinstance(coordinates, LocationOptionsResponse):
        return coordinates

    latitude = coordinates.latitude.strip()
    longitude = coordinates.longitude.strip()
    try:
        weather = await fetch_current_weather(latitude, longitude)
        gust_kph, wet_bulb_c = _run_conditions(weather)

        return calculate_run_grade(
            average_pace_minutes_per_km=average_pace_minutes_per_km,
            headwind_kph=gust_kph,
            wet_bulb_globe_temperature_c=wet_bulb_c,
        )
    except (requests.RequestException, TimeoutError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve weather data.",
        ) from error


def _run_conditions(weather: dict) -> tuple[float, float]:
    current = weather.get("current")
    if not isinstance(current, dict):
        raise TypeError("Weather data must contain current conditions.")

    values = []
    for name in ("gust_kph", "wetbulb_c"):
        value = current.get(name)
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"Current {name} must be a number.")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"Current {name} must be finite.")
        values.append(number)

    gust_kph, wet_bulb_c = values
    if gust_kph < 0:
        raise ValueError("Current gust_kph cannot be negative.")
    return gust_kph, wet_bulb_c
