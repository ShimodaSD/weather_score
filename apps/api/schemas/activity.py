"""Garmin activity API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ActivityIndexResponse(BaseModel):
    """Lightweight activity entry for dashboard navigation."""

    activity_id: str
    started_at: datetime
    activity_type: str
    name: str | None = None


class ActivityResponse(BaseModel):
    """An activity summary suitable for timelines, charts, and detail cards."""

    activity_id: str
    activity_type: str
    name: str | None = None
    started_at: datetime
    elapsed_seconds: float = Field(ge=0)
    moving_seconds: float | None = Field(default=None, ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    average_pace_seconds_per_km: float | None = Field(default=None, gt=0)
    average_speed_kph: float | None = Field(default=None, ge=0)
    average_heart_rate_bpm: int | None = Field(default=None, ge=0)
    maximum_heart_rate_bpm: int | None = Field(default=None, ge=0)
    calories: int | None = Field(default=None, ge=0)
    average_cadence_per_minute: float | None = Field(default=None, ge=0)
    elevation_gain_m: float | None = Field(default=None, ge=0)
    elevation_loss_m: float | None = Field(default=None, ge=0)
    average_temperature_c: float | None = None
    training_effect: float | None = Field(default=None, ge=0)
    anaerobic_training_effect: float | None = Field(default=None, ge=0)


class ActivityDetailResponse(ActivityResponse):
    """Activity summary and all directly related GarminDB rows."""

    activity: dict[str, object]
    steps_activity: dict[str, object] | None = None
    cycle_activity: dict[str, object] | None = None
    climbing_activity: dict[str, object] | None = None
    paddle_activity: dict[str, object] | None = None
    laps: list[dict[str, object]]
    splits: list[dict[str, object]]
    records: list[dict[str, object]]
    activity_devices: list[dict[str, object]]
    devices: list[dict[str, object]]
    device_info: list[dict[str, object]]
    files: list[dict[str, object]]


class RunningPrediction(BaseModel):
    """One target estimate or study-parameter range."""

    distance_km: float = Field(gt=0)
    predicted_seconds: float | None = Field(default=None, gt=0)
    low_seconds: float = Field(gt=0)
    high_seconds: float = Field(gt=0)


class RunningPredictionBasis(BaseModel):
    """A recorded race-distance effort used to fit or anchor the model."""

    distance_km: float = Field(gt=0)
    moving_seconds: float = Field(gt=0)
    source_activity_id: str
    source_distance_km: float = Field(gt=0)
    source_started_at: datetime


class RunningPredictionsResponse(BaseModel):
    """All available target estimates from valid running activities."""

    run_count: int = Field(ge=0)
    longest_run_km: float | None = Field(default=None, gt=0)
    season_start_at: datetime | None = None
    season_end_at: datetime | None = None
    model_status: Literal["fitted", "range", "no_benchmark"]
    vm_mps: float | None = None
    endurance_index: float | None = None
    basis: list[RunningPredictionBasis]
    predictions: list[RunningPrediction]
