"""Garmin activity API schemas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class GarminSyncProgress(BaseModel):
    """File transfer progress for the current process's Garmin sync."""

    phase: Literal[
        "idle", "checking", "downloading", "importing", "complete", "failed"
    ] = "idle"
    downloaded_files: int = Field(default=0, ge=0)
    total_files: int | None = Field(default=None, ge=0)


class ActivityIndexResponse(BaseModel):
    """Lightweight activity entry for dashboard navigation."""

    activity_id: str
    started_at: datetime
    activity_type: str
    name: str | None = None
    distance_km: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class ActivityTssResponse(BaseModel):
    """Training load and the inputs used for an activity calculation."""

    activity_id: str
    tss: float = Field(ge=0, allow_inf_nan=False)
    method: Literal["cycling_power", "running_pace_estimate", "heart_rate_estimate"]
    duration_seconds: float = Field(gt=0, allow_inf_nan=False)
    intensity_factor: float = Field(ge=0, allow_inf_nan=False)
    intensity: float = Field(ge=0, allow_inf_nan=False)
    threshold: float = Field(gt=0, allow_inf_nan=False)
    intensity_unit: Literal["W", "m/s", "bpm"]
    warnings: list[str]


class WeeklyTssResponse(BaseModel):
    """Monday-to-Sunday load total and coverage of recorded activities."""

    week_start: date
    week_end: date
    tss: float | None = Field(ge=0, allow_inf_nan=False)
    threshold_heart_rate_bpm: int = Field(ge=30, le=250)
    scored_activity_count: int = Field(ge=0)
    excluded_activity_count: int = Field(ge=0)


class WeeklyTrainingResponse(WeeklyTssResponse):
    """Weekly sport distances and combined training load."""

    running_km: float | None = Field(ge=0, allow_inf_nan=False)
    cycling_km: float | None = Field(ge=0, allow_inf_nan=False)


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


class RunningImpactActivity(BaseModel):
    """A recorded run and its estimated training impulse."""

    activity_id: str = Field(
        description="Garmin activity identifier.", examples=["12345"]
    )
    started_at: datetime = Field(description="Recorded start time.")
    distance_km: float = Field(gt=0, description="Recorded distance in kilometres.")
    moving_seconds: float = Field(gt=0, description="Moving time in seconds.")
    relative_speed: float = Field(
        gt=0, description="Average speed divided by the fitted crossover speed."
    )
    trimp: float = Field(
        gt=0, description="Estimated training impulse points, not fitness gained."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "activity_id": "12345",
                    "started_at": "2026-09-24T06:00:00Z",
                    "distance_km": 4.5,
                    "moving_seconds": 1800,
                    "relative_speed": 0.75,
                    "trimp": 60.78,
                }
            ]
        }
    }


class RunningImpactResponse(BaseModel):
    """Study-based running training load and the model used to calculate it."""

    model: RunningPredictionsResponse = Field(
        description="Personal running model and its benchmark efforts."
    )
    coefficients: Literal["male", "female"] = Field(
        description="The study's selected coefficient set."
    )
    activities: list[RunningImpactActivity] = Field(
        description="Eligible runs in the model's 180-day window; empty if no personal model can be fitted."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "model": {
                        "run_count": 0,
                        "longest_run_km": None,
                        "season_start_at": None,
                        "season_end_at": None,
                        "model_status": "no_benchmark",
                        "vm_mps": None,
                        "endurance_index": None,
                        "basis": [],
                        "predictions": [],
                    },
                    "coefficients": "male",
                    "activities": [],
                }
            ]
        }
    }
