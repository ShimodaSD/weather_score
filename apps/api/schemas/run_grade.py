"""Pace-aware run grading API schemas."""

from pydantic import BaseModel, Field


class RunGradeRequest(BaseModel):
    """Normalized conditions used by the run scoring engine."""

    average_pace_seconds_per_km: float = Field(
        gt=0,
        description="Average moving pace in seconds per kilometre.",
        examples=[300],
    )
    headwind_kph: float = Field(
        description=(
            "Wind component along the route: positive for a headwind and "
            "negative for a tailwind."
        ),
        examples=[12],
    )
    wet_bulb_globe_temperature_c: float = Field(
        ge=-50,
        le=60,
        description="Wet-bulb globe temperature in degrees Celsius.",
        examples=[15],
    )


class RunGradeResponse(BaseModel):
    """Pace-aware run suitability and factor breakdown."""

    score: float = Field(ge=0, le=100)
    running_speed_kph: float
    relative_air_speed_kph: float
    wind_metabolic_change_percent: float
    thermal_performance_loss_percent: float = Field(ge=0)
