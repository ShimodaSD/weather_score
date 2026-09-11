"""Weather-based activity scoring endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

try:
    from ..schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from ..schemas.score import ScoreResponse, TrainingRunType
    from ..services.scoring import score_activity_at_address
except ImportError:
    from schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from schemas.score import ScoreResponse, TrainingRunType
    from services.scoring import score_activity_at_address

router = APIRouter(prefix="/score", tags=["Score"])


@router.get("/run", response_model=ScoreResponse, summary="Score running conditions")
async def score_run(
    address: str,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> float | ErrorResponse | LocationOptionsResponse:
    """Score the running conditions at an address."""
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Latitude and longitude must be provided together.")
    coordinates = None
    if latitude is not None and longitude is not None:
        coordinates = CoordinatesResponse(latitude=str(latitude), longitude=str(longitude))
    return await score_activity_at_address(address, coordinates=coordinates)


@router.get(
    "/run/by-type",
    response_model=ScoreResponse,
    summary="Score conditions for a running workout type",
)
async def score_run_by_type(
    address: str,
    training_type: TrainingRunType,
) -> float | ErrorResponse | LocationOptionsResponse:
    """Score conditions for a specific running workout type."""
    return await score_activity_at_address(address, training_type)
