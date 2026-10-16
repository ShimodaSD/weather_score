"""Single-account athlete profile contract."""

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    """Editable athlete name and heart-rate threshold."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    threshold_heart_rate_bpm: int = Field(ge=30, le=250, strict=True)


class ProfileResponse(BaseModel):
    """Saved settings; name is unset until the profile is completed."""

    name: str | None
    threshold_heart_rate_bpm: int = Field(ge=30, le=250)
