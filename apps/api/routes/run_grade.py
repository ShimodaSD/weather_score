"""HTTP contract for pace-aware run grading."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

try:
    from ..schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from ..schemas.run_grade import RunGradeRequest, RunGradeResponse
    from ..services.scoring import grade_run_at_address
except ImportError:
    from schemas.location import (
        CoordinatesResponse,
        ErrorResponse,
        LocationOptionsResponse,
    )
    from schemas.run_grade import RunGradeRequest, RunGradeResponse
    from services.scoring import grade_run_at_address

router = APIRouter(prefix="/grade", tags=["Grade"])


@router.post(
    "/run",
    response_model=RunGradeResponse | LocationOptionsResponse | ErrorResponse,
    summary="Grade an average pace using current conditions at an address",
)
async def grade_run(
    address: str,
    request: RunGradeRequest,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> RunGradeResponse | LocationOptionsResponse | ErrorResponse:
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=422, detail="Latitude and longitude must be provided together."
        )
    coordinates = None
    if latitude is not None and longitude is not None:
        coordinates = CoordinatesResponse(
            latitude=str(latitude), longitude=str(longitude)
        )
    result = await grade_run_at_address(
        address,
        request.average_pace_minutes_per_km,
        coordinates=coordinates,
    )
    if isinstance(result, (ErrorResponse, LocationOptionsResponse)):
        return result
    return RunGradeResponse.model_validate(result, from_attributes=True)
