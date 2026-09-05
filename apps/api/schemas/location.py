"""Location API schemas."""

from pydantic import BaseModel


class CoordinatesResponse(BaseModel):
    """Coordinates resolved from a postal address."""

    latitude: str
    longitude: str


class ErrorResponse(BaseModel):
    """Error returned as part of an existing successful response contract."""

    error: str
