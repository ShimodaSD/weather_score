"""Address geocoding service."""

import asyncio

import requests
from fastapi import HTTPException, status

try:
    from ..schemas.location import CoordinatesResponse
except ImportError:
    from schemas.location import CoordinatesResponse

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {
    "User-Agent": "wind-score/1.0 (contact: danieloxshimoda@gmail.com)",
    "Referer": "http://localhost:8000/",
}


async def geocode_address(address: str) -> CoordinatesResponse | None:
    """Resolve an address using OpenStreetMap Nominatim."""
    try:
        response = await asyncio.to_thread(
            requests.get,
            NOMINATIM_SEARCH_URL,
            params={"q": address, "format": "json", "limit": 1},
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
    return CoordinatesResponse(
        latitude=str(data[0]["lat"]),
        longitude=str(data[0]["lon"]),
    )
