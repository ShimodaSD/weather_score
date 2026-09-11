"""Location endpoints."""

from fastapi import APIRouter

try:
    from ..schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from ..services.geocoding import geocode_address
except ImportError:
    from schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from services.geocoding import geocode_address

router = APIRouter(tags=["Location"])


@router.get(
    "/address-to-lat-long",
    response_model=CoordinatesResponse | LocationOptionsResponse | ErrorResponse,
    summary="Get latitude and longitude for an address",
)
async def address_to_lat_long(
    address: str,
) -> CoordinatesResponse | LocationOptionsResponse | ErrorResponse:
    """Resolve an address to latitude and longitude."""
    coordinates = await geocode_address(address)
    if coordinates is None:
        return ErrorResponse(error="Address not found")
    return coordinates
