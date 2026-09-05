"""Weather retrieval and activity scoring orchestration."""

import asyncio
import math
from numbers import Real

import requests
from fastapi import HTTPException, status

from weather_score.application.main import generate_grade, generate_grade_by_type
from weather_score.application.run_grade import RunGrade, calculate_run_grade
from weather_score.weather.providers.openmeteo import get_openmeteo_altitude
from weather_score.weather.providers.weather_api import get_weatherapi_lat_long

try:
    from ..schemas.location import ErrorResponse
    from ..schemas.score import TrainingRunType
    from .geocoding import geocode_address
except ImportError:
    from schemas.location import ErrorResponse
    from schemas.score import TrainingRunType

    from services.geocoding import geocode_address


async def score_address(
    address: str,
    training_type: TrainingRunType | None = None,
) -> float | ErrorResponse:
    """Fetch conditions for an address and calculate its activity score."""
    coordinates = await geocode_address(address)
    if coordinates is None:
        return ErrorResponse(
            error="Could not retrieve latitude and longitude for the given address."
        )

    latitude = coordinates.latitude.strip()
    longitude = coordinates.longitude.strip()
    try:
        weather, altitude = await asyncio.gather(
            get_weatherapi_lat_long(latitude, longitude),
            get_openmeteo_altitude(latitude, longitude),
        )
        if training_type is not None:
            return await generate_grade_by_type(weather, altitude, training_type)
        return await generate_grade(weather, altitude)
    except (requests.RequestException, TimeoutError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve weather data.",
        ) from error


async def grade_run_address(
    address: str,
    average_pace_minutes_per_km: float,
) -> RunGrade | ErrorResponse:
    """Fetch current conditions for an address and grade a running pace."""
    coordinates = await geocode_address(address)
    if coordinates is None:
        return ErrorResponse(
            error="Could not retrieve latitude and longitude for the given address."
        )

    latitude = coordinates.latitude.strip()
    longitude = coordinates.longitude.strip()
    try:
        weather = await get_weatherapi_lat_long(latitude, longitude)
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
