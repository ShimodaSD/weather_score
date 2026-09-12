from datetime import UTC, datetime, timedelta
from math import isclose

from weather_score.application.running_predictions import (
    _predict_time,
    calculate_running_predictions,
)


def test_predictions_fit_two_consistent_race_distance_efforts():
    started_at = datetime(2026, 9, 11, tzinfo=UTC)
    vm, gamma = 4.5, 0.08
    runs = [
        {
            "activity_id": str(distance),
            "started_at": started_at,
            "distance_km": distance,
            "moving_seconds": _predict_time(distance, vm, gamma),
        }
        for distance in (5.0, 10.0)
    ]

    result = calculate_running_predictions(runs)

    assert result["model_status"] == "fitted"
    assert len(result["basis"]) == 2
    assert isclose(result["vm_mps"], vm, rel_tol=1e-6)
    assert [item["distance_km"] for item in result["predictions"]] == [5, 10, 21, 42]
    assert isclose(
        result["predictions"][3]["predicted_seconds"],
        _predict_time(42, vm, gamma),
        rel_tol=1e-6,
    )
    assert all(
        item["low_seconds"] == item["high_seconds"] for item in result["predictions"]
    )


def test_single_recent_benchmark_returns_bounded_ranges_not_fitted_times():
    started_at = datetime(2026, 9, 11, tzinfo=UTC)
    result = calculate_running_predictions(
        [
            {
                "activity_id": "old-5k",
                "started_at": started_at - timedelta(days=200),
                "distance_km": 5.0,
                "moving_seconds": 1300.0,
            },
            {
                "activity_id": "recent-10k",
                "started_at": started_at,
                "distance_km": 10.0,
                "moving_seconds": 2700.0,
            },
        ]
    )

    assert result["run_count"] == 1
    assert result["model_status"] == "range"
    assert [item["source_activity_id"] for item in result["basis"]] == ["recent-10k"]
    assert len(result["predictions"]) == 4
    assert result["predictions"][3]["predicted_seconds"] is None
    assert (
        result["predictions"][3]["low_seconds"]
        < result["predictions"][3]["high_seconds"]
    )


def test_inconsistent_or_invalid_efforts_do_not_claim_a_personal_fit():
    started_at = datetime(2026, 9, 11, tzinfo=UTC)
    result = calculate_running_predictions(
        [
            {
                "activity_id": "5k",
                "started_at": started_at,
                "distance_km": 5.0,
                "moving_seconds": 1350.0,
            },
            {
                "activity_id": "10k",
                "started_at": started_at,
                "distance_km": 10.0,
                "moving_seconds": 2700.0,
            },
            {
                "activity_id": "bad",
                "started_at": started_at,
                "distance_km": float("inf"),
                "moving_seconds": 1.0,
            },
        ]
    )
    assert result["model_status"] == "range"
    assert result["vm_mps"] is None
    assert result["basis"][0]["source_activity_id"] == "10k"
    assert calculate_running_predictions([])["model_status"] == "no_benchmark"
