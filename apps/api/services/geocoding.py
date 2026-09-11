"""Address geocoding service."""

import asyncio

import requests
from fastapi import HTTPException, status

try:
    from ..schemas.location import (
        CoordinatesResponse,
        LocationOption,
        LocationOptionsResponse,
    )
except ImportError:
    from schemas.location import (
        CoordinatesResponse,
        LocationOption,
        LocationOptionsResponse,
    )

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {
    "User-Agent": "wind-score/1.0 (contact: danieloxshimoda@gmail.com)",
    "Referer": "http://localhost:8000/",
}


async def geocode_address(
    address: str,
) -> CoordinatesResponse | LocationOptionsResponse | None:
    """Resolve an address using OpenStreetMap Nominatim."""
    try:
        response = await asyncio.to_thread(
            requests.get,
            NOMINATIM_SEARCH_URL,
            params={"q": address, "format": "json", "limit": 5},
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve coordinates.",
        ) from error

    if not data:
        return None
    if len(data) > 1:
        return LocationOptionsResponse(
            options=[
                LocationOption(
                    name=option["display_name"],
                    latitude=str(option["lat"]),
                    longitude=str(option["lon"]),
                )
                for option in data
            ]
        )
    return CoordinatesResponse(
        latitude=str(data[0]["lat"]),
        longitude=str(data[0]["lon"]),
    )
