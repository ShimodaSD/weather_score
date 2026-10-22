from datetime import UTC, date, datetime

from weather_score.application.weekly_training import calculate_weekly_training


def test_weekly_training_combines_tss_but_separates_distance():
    run = {
        "started_at": datetime(2026, 12, 28, tzinfo=UTC),
        "activity_type": "running",
        "distance_km": 5,
        "average_heart_rate_bpm": 150,
        "elapsed_seconds": 1800,
    }
    ride = run | {
        "started_at": datetime(2027, 1, 3, tzinfo=UTC),
        "activity_type": "cycling",
        "distance_km": 25,
    }
    missing_hr = run | {"distance_km": 2, "average_heart_rate_bpm": None}
    next_week = run | {"started_at": datetime(2027, 1, 4, tzinfo=UTC), "distance_km": None}
    weeks = calculate_weekly_training(
        [run, ride, missing_hr, next_week], date(2026, 12, 28), 157
    )
    assert len(weeks) == 12
    assert weeks[0]["running_km"] == 7
    assert weeks[0]["cycling_km"] == 25
    assert weeks[0]["tss"] == 80
    assert weeks[0]["excluded_activity_count"] == 1
    assert weeks[1]["running_km"] is None
    assert weeks[2]["running_km"] == weeks[2]["cycling_km"] == weeks[2]["tss"] == 0
    for distance in (-1, float("nan"), float("inf"), "5", True):
        result = calculate_weekly_training(
            [run | {"distance_km": distance, "average_heart_rate_bpm": None}],
            date(2026, 12, 28),
            157,
        )
        assert result[0]["running_km"] is None
        assert result[0]["tss"] is None
