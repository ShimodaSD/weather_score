"""Weather retrieval and activity scoring orchestration."""

import asyncio

import requests
from fastapi import HTTPException, status

from weather_score.application.main import generate_grade, generate_grade_by_type
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
