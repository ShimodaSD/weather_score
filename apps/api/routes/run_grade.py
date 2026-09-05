"""HTTP contract for pace-aware run grading."""

from fastapi import APIRouter

from weather_score.application.run_grade import calculate_run_grade

try:
    from ..schemas.run_grade import RunGradeRequest, RunGradeResponse
except ImportError:
    from schemas.run_grade import RunGradeRequest, RunGradeResponse

router = APIRouter(prefix="/grade", tags=["Grade"])


@router.post(
    "/run",
    response_model=RunGradeResponse,
    summary="Grade running conditions for an average pace",
)
async def grade_run(request: RunGradeRequest) -> RunGradeResponse:
    result = calculate_run_grade(**request.model_dump())
    return RunGradeResponse.model_validate(result, from_attributes=True)
