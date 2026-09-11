"""Location API schemas."""

from pydantic import BaseModel


class CoordinatesResponse(BaseModel):
    """Coordinates resolved from a postal address."""

    latitude: str
    longitude: str


class LocationOption(CoordinatesResponse):
    """A named location returned for an ambiguous address."""

    name: str


class LocationOptionsResponse(BaseModel):
    """Possible locations for an ambiguous address."""

    options: list[LocationOption]


class ErrorResponse(BaseModel):
    """Error returned as part of an existing successful response contract."""

    error: str
