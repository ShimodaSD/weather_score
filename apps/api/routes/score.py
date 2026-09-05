"""Weather-based activity scoring endpoints."""

from fastapi import APIRouter

try:
    from ..schemas.location import ErrorResponse
    from ..schemas.score import ScoreResponse, TrainingRunType
    from ..services.scoring import score_address
except ImportError:
    from schemas.location import ErrorResponse
    from schemas.score import ScoreResponse, TrainingRunType
    from services.scoring import score_address

router = APIRouter(prefix="/score", tags=["Score"])


@router.get("/run", response_model=ScoreResponse, summary="Score running conditions")
async def score_run(address: str) -> float | ErrorResponse:
    """Score the running conditions at an address."""
    return await score_address(address)


@router.get(
    "/run/by-type",
    response_model=ScoreResponse,
    summary="Score conditions for a running workout type",
)
async def score_run_by_type(
    address: str,
    training_type: TrainingRunType,
) -> float | ErrorResponse:
    """Score conditions for a specific running workout type."""
    return await score_address(address, training_type)
