"""Weather-based activity scoring endpoints."""

from fastapi import APIRouter, HTTPException

try:
    from ..schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from ..schemas.score import ScoreResponse
    from ..services.scoring import score_activity_at_address
except ImportError:
    from schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from schemas.score import ScoreResponse
    from services.scoring import score_activity_at_address

router = APIRouter(prefix="/score", tags=["Score"])


@router.get(
    "/run",
    response_model=ScoreResponse,
    summary="Score running conditions without pace data",
)
async def score_run(
    address: str,
    latitude: str | None = None,
    longitude: str | None = None,
) -> float | ErrorResponse | LocationOptionsResponse:
    """Score current weather and elevation for running."""
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Latitude and longitude must be provided together.")
    coordinates = (
        CoordinatesResponse(latitude=latitude, longitude=longitude)
        if latitude is not None and longitude is not None
        else None
    )
    return await score_activity_at_address(address, coordinates=coordinates)

