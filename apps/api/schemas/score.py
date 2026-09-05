"""Activity score API schemas."""

from typing import Annotated, Literal

from pydantic import Field

from .location import ErrorResponse

TrainingRunType = Literal["easy", "long", "threshold", "interval", "speed"]
BoundedScore = Annotated[float, Field(ge=0, le=100)]
ScoreResponse = BoundedScore | ErrorResponse
