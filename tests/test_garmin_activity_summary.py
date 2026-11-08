"""Tests for mapping Garmin summaries into the activity API's units."""

from datetime import time
from enum import Enum

import pytest

from weather_score.garmin_activity_summary import map_activity_summary


class Sport(Enum):
    running = 1
    training = 2


def test_summary_uses_fit_session_and_converts_distance():
    result = map_activity_summary(
        {
            "activityId": 42,
            "activityName": "Run",
            "startTimeLocal": "2026-01-01 12:00:00",
            "elapsedDuration": 3600,
            "movingDuration": 3500,
            "distance": 10000,
        },
        {
            "sport": Sport.running,
            "total_distance": 9.8,
            "avg_heart_rate": 145,
            "avg_temperature": 29,
            "total_elapsed_time": time(1, 0, 0, 500000),
        },
        {"summaryDTO": {"averageTemperature": 28.5}},
    )
    assert result["activity_id"] == "42"
    assert result["sport"] == "running"
    assert result["distance"] == 9.8
    assert result["avg_hr"] == 145
    assert result["elapsed_time"] == time(1, 0)
    assert result["avg_temperature"] == 28.5
    assert result["stop_time"].isoformat() == "2026-01-01T13:00:00"


def test_strength_training_uses_garmin_activity_type():
    result = map_activity_summary(
        {
            "activityId": 1,
            "startTimeLocal": "2026-01-01 12:00:00",
            "elapsedDuration": 20,
            "movingDuration": 20,
            "activityType": {"typeKey": "strength_training"},
        },
        {"sport": Sport.training},
    )
    assert result["sport"] == "fitness_equipment"


@pytest.mark.parametrize("seconds", [-1, 86400])
def test_rejects_unrepresentable_duration(seconds):
    with pytest.raises(ValueError, match="duration"):
        map_activity_summary(
            {
                "activityId": 1,
                "startTimeLocal": "2026-01-01 12:00:00",
                "elapsedDuration": seconds,
            },
            {},
        )
