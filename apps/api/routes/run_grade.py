"""HTTP contract for pace-aware run grading."""

from fastapi import APIRouter

try:
    from ..schemas.location import ErrorResponse
    from ..schemas.run_grade import RunGradeRequest, RunGradeResponse
    from ..services.scoring import grade_run_address
except ImportError:
    from schemas.location import ErrorResponse
    from schemas.run_grade import RunGradeRequest, RunGradeResponse
    from services.scoring import grade_run_address

router = APIRouter(prefix="/grade", tags=["Grade"])


@router.post(
    "/run",
    response_model=RunGradeResponse | ErrorResponse,
    summary="Grade an average pace using current conditions at an address",
)
async def grade_run(
    address: str,
    request: RunGradeRequest,
) -> RunGradeResponse | ErrorResponse:
    result = await grade_run_address(
        address,
        request.average_pace_minutes_per_km,
    )
    if isinstance(result, ErrorResponse):
        return result
    return RunGradeResponse.model_validate(result, from_attributes=True)
