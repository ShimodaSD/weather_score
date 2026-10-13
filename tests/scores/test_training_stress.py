import pytest
from weather_score.application.training_stress import (
    calculate_activity_tss,
    calculate_tss_total,
)


def test_weekly_total_reuses_activity_estimates_and_reports_exclusions():
    activity = {
        "activity_type": "running",
        "elapsed_seconds": 3600,
        "average_heart_rate_bpm": 157,
    }
    rows = [
        activity,
        activity | {"activity_type": "cycling", "elapsed_seconds": 7200},
        activity | {"average_heart_rate_bpm": None},
        activity | {"activity_type": "swimming"},
        activity | {"elapsed_seconds": -1},
        activity | {"average_heart_rate_bpm": float("nan")},
    ]
    assert calculate_tss_total(rows, 157) == {
        "tss": 300,
        "scored_activity_count": 2,
        "excluded_activity_count": 4,
    }
    assert calculate_tss_total([activity], 170)["tss"] == 70
    assert calculate_tss_total([], 157) == {
        "tss": 0,
        "scored_activity_count": 0,
        "excluded_activity_count": 0,
    }
    assert calculate_tss_total(rows[2:], 157) == {
        "tss": None,
        "scored_activity_count": 0,
        "excluded_activity_count": 4,
    }
    with pytest.raises(ValueError):
        calculate_tss_total([], 0)


@pytest.mark.parametrize(
    "ratio,expected",
    [
        (0.8, 30),
        (0.85, 55),
        (0.90, 70),
        (0.95, 80),
        (1, 100),
        (1.03, 120),
        (1.06, 120),
        (1.061, 140),
    ],
)
def test_heart_rate_estimate_uses_threshold_zones(ratio, expected):
    result = calculate_activity_tss(
        "running",
        threshold_heart_rate_bpm=157,
        average_heart_rate_bpm=157 * ratio,
        elapsed_seconds=3600,
    )
    assert result["tss"] == expected
    assert result["threshold"] == 157
    assert result["intensity_unit"] == "bpm"
    assert result["method"] == "heart_rate_estimate"


def test_heart_rate_estimate_duration_and_cycling_zones():
    result = calculate_activity_tss(
        "cycling",
        threshold_heart_rate_bpm=157,
        average_heart_rate_bpm=157 * 0.82,
        elapsed_seconds=7200,
        moving_seconds=0,
    )
    assert result["tss"] == 110
    assert result["duration_seconds"] == 7200
    assert "pauses" in result["warnings"][1]


@pytest.mark.parametrize(
    "field,value",
    [
        ("average_heart_rate_bpm", None),
        ("average_heart_rate_bpm", 0),
        ("average_heart_rate_bpm", 251),
        ("average_heart_rate_bpm", float("nan")),
        ("threshold_heart_rate_bpm", 29),
        ("threshold_heart_rate_bpm", float("inf")),
        ("elapsed_seconds", None),
        ("elapsed_seconds", -1),
        ("ftp_watts", 250),
        ("threshold_pace_seconds_per_km", 300),
    ],
)
def test_heart_rate_rejects_invalid_missing_and_mixed_inputs(field, value):
    inputs = {
        "threshold_heart_rate_bpm": 157,
        "average_heart_rate_bpm": 150,
        "elapsed_seconds": 3600,
    }
    inputs[field] = value
    with pytest.raises(ValueError):
        calculate_activity_tss("running", **inputs)


@pytest.mark.parametrize(
    "duration,power,expected",
    [
        (3600, 250, 100),
        (3600, 125, 25),
        (7200, 250, 200),
        (1800, 300, 72),
        (3600, 0, 0),
    ],
)
def test_cycling_threshold_duration_and_intensity(duration, power, expected):
    result = calculate_activity_tss(
        "cycling",
        duration_seconds=duration,
        normalized_power_watts=power,
        ftp_watts=250,
    )
    assert result["tss"] == expected
    assert result["method"] == "cycling_power"
    assert result["intensity_factor"] == power / 250


@pytest.mark.parametrize(
    "duration,distance,expected",
    [(3600, 12, 100), (3600, 6, 25), (7200, 24, 200), (1800, 7.2, 72)],
)
def test_running_uses_speed_ratio_not_inverse_pace(duration, distance, expected):
    result = calculate_activity_tss(
        "running",
        moving_seconds=duration,
        distance_km=distance,
        threshold_pace_seconds_per_km=300,
    )
    assert result["tss"] == expected
    assert result["method"] == "running_pace_estimate"
    assert result["intensity_unit"] == "m/s"
    assert result["threshold"] == pytest.approx(10 / 3)
    assert "not normalized graded pace" in result["warnings"][0]


@pytest.mark.parametrize(
    "field", ["moving_seconds", "distance_km", "threshold_pace_seconds_per_km"]
)
@pytest.mark.parametrize(
    "value", [None, 0, -1, float("nan"), float("inf"), True, "300"]
)
def test_running_rejects_missing_and_invalid_inputs(field, value):
    inputs = {
        "moving_seconds": 3600,
        "distance_km": 12,
        "threshold_pace_seconds_per_km": 300,
    }
    inputs[field] = value
    with pytest.raises((TypeError, ValueError)):
        calculate_activity_tss("running", **inputs)


@pytest.mark.parametrize(
    "field", ["duration_seconds", "normalized_power_watts", "ftp_watts"]
)
@pytest.mark.parametrize("value", [None, -1, float("nan"), float("inf"), True, "250"])
def test_cycling_rejects_missing_and_invalid_inputs(field, value):
    inputs = {"duration_seconds": 3600, "normalized_power_watts": 250, "ftp_watts": 250}
    inputs[field] = value
    with pytest.raises((TypeError, ValueError)):
        calculate_activity_tss("cycling", **inputs)


@pytest.mark.parametrize(
    "inputs",
    [
        {"duration_seconds": 0, "normalized_power_watts": 250, "ftp_watts": 250},
        {"duration_seconds": 3600, "normalized_power_watts": 250, "ftp_watts": 0},
        {
            "duration_seconds": 3600,
            "normalized_power_watts": 1e308,
            "ftp_watts": 1e-308,
        },
        {"duration_seconds": 3600, "normalized_power_watts": 1e200, "ftp_watts": 1},
        {"duration_seconds": 10**400, "normalized_power_watts": 250, "ftp_watts": 250},
    ],
)
def test_cycling_rejects_zero_divisors_and_extreme_values(inputs):
    with pytest.raises(ValueError):
        calculate_activity_tss("cycling", **inputs)


def test_unsupported_sports_and_mismatched_inputs_are_rejected():
    with pytest.raises(ValueError, match="supported"):
        calculate_activity_tss("swimming")
    with pytest.raises(ValueError, match="Running uses"):
        calculate_activity_tss("running", ftp_watts=250)
    with pytest.raises(ValueError, match="Cycling uses"):
        calculate_activity_tss("cycling", threshold_pace_seconds_per_km=300)
    with pytest.raises(ValueError, match="extreme"):
        calculate_activity_tss(
            "running",
            moving_seconds=1e-308,
            distance_km=1e308,
            threshold_pace_seconds_per_km=300,
        )
