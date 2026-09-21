"""Schemas for persisted Garmin route grades."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ActivityGradeSegmentResponse(BaseModel):
    """Weather grade for one route segment."""

    index: int = Field(ge=1)
    start_distance_m: float = Field(ge=0)
    end_distance_m: float = Field(gt=0)
    distance_m: float = Field(gt=0)
    elapsed_seconds: float = Field(gt=0)
    pace_minutes_per_km: float = Field(gt=0)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    route_bearing_degrees: float | None = Field(default=None, ge=0, lt=360)
    recorded_at: datetime
    score: float = Field(ge=0, le=100)
    running_speed_kph: float = Field(gt=0)
    relative_air_speed_kph: float = Field(ge=0)
    wind_metabolic_change_percent: float
    thermal_performance_loss_percent: float = Field(ge=0)
    gust_kph: float | None = Field(default=None, ge=0)
    wind_kph: float = Field(ge=0)
    wind_degree: float | None = Field(default=None, ge=0, le=360)
    headwind_kph: float | None = None
    temperature_c: float | None = Field(default=None, ge=-50, le=60)
    wet_bulb_c: float | None = Field(default=None, ge=-50, le=60)
    wbgt_c: float | None = Field(default=None, ge=-50, le=60)
    weather_at: datetime


class ActivityGradeResponse(BaseModel):
    """Current persisted state of one activity-grade job."""

    activity_id: str
    status: Literal["processing", "complete", "failed"]
    score: float | None = Field(default=None, ge=0, le=100)
    segments: list[ActivityGradeSegmentResponse]
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
