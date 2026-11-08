"""Exercise the independent activity import's safety checks and conversions."""

from datetime import time
from enum import Enum
from types import SimpleNamespace

import pytest

import weather_score.garmin_activity_import as importer
from weather_score.garmin_activity_import import (
    _apply_zones,
    _sport_data,
    import_activity,
)


class ZoneType(Enum):
    session = 1
    lap = 2


def test_running_metrics_use_summary_units_and_fit_fallback():
    activity = {"activity_id": "42", "sport": "running"}
    session = {"avg_step_length": 1200.0, "avg_vertical_oscillation": 90.0}
    summary = {
        "avgStrideLength": 123.4,
        "avgVerticalOscillation": 9.5,
        "averageRunningCadenceInStepsPerMinute": 171.5,
    }
    _, values = _sport_data(activity, session, summary, {}, None)
    assert (
        values["avg_step_length"],
        values["avg_vertical_oscillation"],
        values["avg_steps_per_min"],
    ) == (123.4, 9.5, 171.5)
    _, fallback = _sport_data(activity, session, {}, {}, None)
    assert (fallback["avg_step_length"], fallback["avg_vertical_oscillation"]) == (
        120.0,
        9.0,
    )


def test_zone_data_is_attached_to_session_and_lap():
    values = [time.min, time(0, 1), time(0, 2), time(0, 3), time(0, 4), time(0, 5)]
    fit = SimpleNamespace(
        hr_zones_timer=[
            SimpleNamespace(
                fields={
                    "hr_zones_timer_type": ZoneType.session,
                    "hr_zones_time": values,
                    "hr_zones": [100, 110, 120, 130, 140],
                }
            ),
            SimpleNamespace(
                fields={
                    "hr_zones_timer_type": ZoneType.lap,
                    "record_num": 0,
                    "hr_zones_time": values,
                }
            ),
        ]
    )
    activity, laps = {}, [{}]
    _apply_zones(fit, activity, laps)
    assert activity["hrz_5_hr"] == 140
    assert activity["hrz_1_time"] == time(0, 1)
    assert laps[0]["hrz_5_time"] == time(0, 5)


def test_unknown_lap_is_rejected():
    fit = SimpleNamespace(
        hr_zones_timer=[
            SimpleNamespace(
                fields={"hr_zones_timer_type": ZoneType.lap, "record_num": 2}
            )
        ]
    )
    with pytest.raises(ValueError, match="unknown lap"):
        _apply_zones(fit, {}, [{}])


def test_mismatched_activity_ids_do_not_start_import():
    with pytest.raises(ValueError, match="IDs differ"):
        import_activity(None, {"activityId": 1}, {"activityId": 2}, None)


def test_fit_filename_must_match_the_activity(tmp_path):
    with pytest.raises(ValueError, match="filename"):
        import_activity(None, {"activityId": 1}, {"activityId": 1}, tmp_path / "2.fit")


def test_invalid_heart_rate_threshold_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="threshold"):
        import_activity(
            None,
            {"activityId": 1},
            {"activityId": 1},
            tmp_path / "1.fit",
            threshold_heart_rate_bpm=0,
        )


def test_missing_fit_fails_before_database_use(tmp_path):
    with pytest.raises(FileNotFoundError):
        import_activity(None, {"activityId": 1}, {"activityId": 1}, tmp_path / "1.fit")


def test_invalid_fit_fails_before_database_use(tmp_path):
    path = tmp_path / "1.fit"
    path.write_bytes(b"\x00" * 8 + b".FIT")
    with pytest.raises(ValueError, match="invalid FIT"):
        import_activity(None, {"activityId": 1}, {"activityId": 1}, path)


def test_climbing_splits_fail_before_database_use(tmp_path, monkeypatch):
    path = tmp_path / "1.fit"
    path.write_bytes(b"FIT")
    fit = SimpleNamespace(
        session=[SimpleNamespace(fields={"sport": "rock_climbing"})],
        split=[SimpleNamespace(fields={"grade": 2})],
    )
    monkeypatch.setattr(importer, "validate_fit", lambda _: None)
    monkeypatch.setattr(importer, "File", lambda _: fit)
    with pytest.raises(ValueError, match="Climbing splits"):
        import_activity(None, {"activityId": 1}, {"activityId": 1}, path)
