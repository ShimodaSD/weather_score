from datetime import UTC, datetime
from math import exp

from weather_score.application.running_impact import calculate_running_impact


def test_impact_calculates_study_formula_and_excludes_invalid(monkeypatch):
    now = datetime.now(UTC)
    monkeypatch.setattr(
        "weather_score.application.running_impact.calculate_running_predictions",
        lambda runs: {"vm_mps": 4.0, "season_start_at": now, "season_end_at": now},
    )
    runs = [
        {
            "activity_id": "1",
            "started_at": now,
            "distance_km": 6.0,
            "moving_seconds": 1800.0,
        },
        {
            "activity_id": "2",
            "started_at": now,
            "distance_km": 0.0,
            "moving_seconds": 1800.0,
        },
    ]
    result = calculate_running_impact(runs, "female")
    assert len(result["activities"]) == 1
    run = result["activities"][0]
    ratio = (6000 / 1800) / 4
    assert run["relative_speed"] == ratio
    assert run["trimp"] == 30 * 0.86 * ratio * exp(1.67 * ratio)


def test_impact_without_personal_fit_has_no_estimates():
    assert calculate_running_impact([], "male")["activities"] == []
