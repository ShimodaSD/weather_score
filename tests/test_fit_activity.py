"""Tests for decoding Garmin FIT activity messages."""

from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace

import pytest

from weather_score.fit_activity import decode_activity, decode_fit_sessions


def test_decode_records_and_laps(monkeypatch, tmp_path):
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    fit = SimpleNamespace(
        session=[object()],
        record=[
            SimpleNamespace(
                fields={"timestamp": timestamp, "heart_rate": 140, "distance": 1.2}
            )
        ],
        lap=[
            SimpleNamespace(
                fields={
                    "start_time": timestamp,
                    "timestamp": timestamp,
                    "total_distance": 1.2,
                    "total_ascent": 0,
                }
            )
        ],
        utc_datetime_to_local=lambda value: value.replace(tzinfo=None),
    )
    monkeypatch.setattr("weather_score.fit_activity.File", lambda _: fit)

    result = decode_activity(tmp_path / "activity.fit")

    assert result["records"][0]["hr"] == 140
    assert result["records"][0]["distance"] == 1.2
    assert result["records"][0]["timestamp"].tzinfo is None
    assert result["laps"][0]["distance"] == 1.2
    assert result["laps"][0]["lap"] == 0
    assert result["laps"][0]["ascent"] is None


def test_single_activity_decoder_requires_session_decoding_for_multisport(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        "weather_score.fit_activity.File", lambda _: SimpleNamespace(session=[1, 2])
    )
    with pytest.raises(ValueError, match="Multisport"):
        decode_activity(tmp_path / "activity.fit")


def test_multisport_sessions_partition_records_laps_and_boundary():
    start = datetime(2026, 1, 1, tzinfo=UTC)

    def message(**fields):
        return SimpleNamespace(fields=fields)

    fit = SimpleNamespace(
        session=[
            message(start_time=start, total_elapsed_time=time(0, 1), num_laps=1),
            message(
                start_time=start + timedelta(minutes=1),
                total_elapsed_time=time(0, 1),
                num_laps=1,
            ),
        ],
        record=[
            message(timestamp=start),
            message(timestamp=start + timedelta(minutes=1)),
            message(timestamp=start + timedelta(minutes=2)),
        ],
        lap=[
            message(start_time=start, total_elapsed_time=time(0, 1)),
            message(
                start_time=start + timedelta(minutes=1), total_elapsed_time=time(0, 1)
            ),
        ],
        utc_datetime_to_local=lambda value: value.replace(tzinfo=None),
    )
    sessions = decode_fit_sessions(fit)
    assert [len(session["records"]) for session in sessions] == [1, 2]
    assert [len(session["laps"]) for session in sessions] == [1, 1]
    assert sessions[1]["records"][0]["record"] == 0
    assert sessions[1]["laps"][0]["lap"] == 0


def test_multisport_rejects_unassigned_records():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    message = lambda **fields: SimpleNamespace(fields=fields)
    fit = SimpleNamespace(
        session=[
            message(start_time=start, total_elapsed_time=time(0, 1), num_laps=0),
            message(
                start_time=start + timedelta(minutes=2),
                total_elapsed_time=time(0, 1),
                num_laps=0,
            ),
        ],
        record=[message(timestamp=start + timedelta(seconds=90))],
        lap=[],
    )
    with pytest.raises(ValueError, match="outside session"):
        decode_fit_sessions(fit)


def test_multisport_accepts_subsecond_boundary_rounding():
    start = datetime(2026, 1, 1, tzinfo=UTC)

    def message(**fields):
        return SimpleNamespace(fields=fields)

    fit = SimpleNamespace(
        session=[
            message(
                start_time=start, total_elapsed_time=time(0, 1, 0, 500000), num_laps=0
            ),
            message(
                start_time=start + timedelta(minutes=1),
                total_elapsed_time=time(0, 1),
                num_laps=0,
            ),
        ],
        record=[message(timestamp=start + timedelta(minutes=1))],
        lap=[],
        utc_datetime_to_local=lambda value: value.replace(tzinfo=None),
    )
    result = decode_fit_sessions(fit)
    assert [len(session["records"]) for session in result] == [0, 1]


@pytest.mark.parametrize("overlap,lap_count", [(True, 0), (False, 1)])
def test_multisport_rejects_overlaps_and_missing_laps(overlap, lap_count):
    start = datetime(2026, 1, 1, tzinfo=UTC)

    def message(**fields):
        return SimpleNamespace(fields=fields)

    fit = SimpleNamespace(
        session=[
            message(
                start_time=start, total_elapsed_time=time(0, 1), num_laps=lap_count
            ),
            message(
                start_time=start + timedelta(seconds=30 if overlap else 60),
                total_elapsed_time=time(0, 1),
                num_laps=0,
            ),
        ],
        record=[],
        lap=[],
    )
    with pytest.raises(ValueError, match="overlap|lap count"):
        decode_fit_sessions(fit)
