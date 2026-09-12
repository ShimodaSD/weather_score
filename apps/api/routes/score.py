"""Weather-based activity scoring endpoints."""

from fastapi import APIRouter

try:
    from ..schemas.location import (
        ErrorResponse,
        LocationOptionsResponse,
    )
    from ..schemas.score import ScoreResponse, TrainingRunType
    from ..services.scoring import score_activity_at_address
except ImportError:
    from schemas.location import (
        ErrorResponse,
        LocationOptionsResponse,
    )
    from schemas.score import ScoreResponse, TrainingRunType
    from services.scoring import score_activity_at_address

router = APIRouter(prefix="/score", tags=["Score"])


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
