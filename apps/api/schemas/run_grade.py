"""Pace-aware run grading API schemas."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PACE_PATTERN = re.compile(r"^(\d+):([0-5]\d)$")


class RunGradeRequest(BaseModel):
    """Runner input used with current conditions resolved by address."""

    model_config = ConfigDict(extra="forbid")

    average_pace_minutes_per_km: float = Field(
        gt=0,
        description=(
            "Average moving pace in minutes per kilometre, either as decimal "
            "minutes or a minutes:seconds string."
        ),
        examples=["5:20"],
    )

    @field_validator(
        "average_pace_minutes_per_km",
        mode="before",
        json_schema_input_type=float | str,
    )
    @classmethod
    def parse_pace(cls, value: object) -> object:
        """Convert minutes:seconds pace notation to decimal minutes."""
        if not isinstance(value, str):
            return value

        match = _PACE_PATTERN.fullmatch(value.strip())
        if match is None:
            raise ValueError("pace must use minutes:seconds format, such as 5:20")

        minutes, seconds = (int(part) for part in match.groups())
        return minutes + seconds / 60


class RunGradeResponse(BaseModel):
    """Pace-aware run suitability and factor breakdown."""

    score: float = Field(ge=0, le=100)
    running_speed_kph: float
    relative_air_speed_kph: float
    wind_metabolic_change_percent: float
    thermal_performance_loss_percent: float = Field(ge=0)
