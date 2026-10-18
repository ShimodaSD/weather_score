"""Activity score API schemas."""

from typing import Annotated

from pydantic import Field

from .location import ErrorResponse, LocationOptionsResponse

BoundedScore = Annotated[float, Field(ge=0, le=100)]
ScoreResponse = BoundedScore | ErrorResponse | LocationOptionsResponse
