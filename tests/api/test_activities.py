import importlib
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test")

main = importlib.import_module("apps.api.main")
auth = importlib.import_module("apps.api.security.auth")
garmin = importlib.import_module("apps.api.routes.garmin")

client = TestClient(main.app, raise_server_exceptions=False)

ACTIVITY = {
    "activity_id": "123",
    "activity_type": "running",
    "name": "Morning Run",
    "started_at": datetime(2026, 9, 11, 6, 30, tzinfo=UTC),
    "elapsed_seconds": 1800.0,
    "moving_seconds": 1740.0,
    "distance_km": 5.0,
    "average_pace_seconds_per_km": 348.0,
    "average_speed_kph": 10.34,
    "average_heart_rate_bpm": 150,
    "maximum_heart_rate_bpm": 170,
    "calories": 400,
    "average_cadence_per_minute": 174.0,
    "elevation_gain_m": 30.0,
    "elevation_loss_m": 28.0,
    "average_temperature_c": 22.0,
    "training_effect": 3.2,
    "anaerobic_training_effect": 0.5,
}


def test_activities_require_bearer_token():
    response = client.get("/activities")

    assert response.status_code == 401
    assert client.get("/activities/index").status_code == 401
    assert client.get("/activities/tss/weekly?week_of=2026-09-24").status_code == 401
    assert client.get("/activities/123/summary").status_code == 401
    assert client.get("/activities/running/predictions").status_code == 401
    assert client.post("/activities/sync").status_code == 401
    assert (
        client.get("/activities/123/tss?threshold_pace_seconds_per_km=300").status_code
        == 401
    )


@pytest.mark.parametrize(
    "week_of,start,end",
    [
        ("2026-09-21", date(2026, 9, 21), date(2026, 9, 28)),
        ("2026-09-27", date(2026, 9, 21), date(2026, 9, 28)),
        ("2026-09-28", date(2026, 9, 28), date(2026, 10, 5)),
        ("2027-01-01", date(2026, 12, 28), date(2027, 1, 4)),
    ],
)
def test_weekly_tss_calendar_boundaries_and_saved_threshold(
    monkeypatch, week_of, start, end
):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        garmin,
        "fetch_profile",
        AsyncMock(return_value={"threshold_heart_rate_bpm": 157}),
    )
    fetch = AsyncMock(
        return_value=[ACTIVITY, ACTIVITY | {"average_heart_rate_bpm": None}]
    )
    monkeypatch.setattr(garmin, "fetch_weekly_tss_inputs", fetch)
    response = client.get(
        f"/activities/tss/weekly?week_of={week_of}",
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 200
    assert response.json()["week_start"] == start.isoformat()
    assert response.json()["tss"] == 40
    assert response.json()["scored_activity_count"] == 1
    assert response.json()["excluded_activity_count"] == 1
    assert response.json()["threshold_heart_rate_bpm"] == 157
    fetch.assert_awaited_once_with(start, end)


def test_weekly_tss_empty_week_and_invalid_date(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        garmin,
        "fetch_profile",
        AsyncMock(return_value={"threshold_heart_rate_bpm": 157}),
    )
    monkeypatch.setattr(garmin, "fetch_weekly_tss_inputs", AsyncMock(return_value=[]))
    headers = {"Authorization": "Bearer token"}
    response = client.get("/activities/tss/weekly?week_of=2026-09-24", headers=headers)
    assert response.json()["tss"] == 0
    assert response.json()["week_end"] == "2026-09-27"
    for value in ("invalid", "2026-02-30", "9999-12-31"):
        assert (
            client.get(
                f"/activities/tss/weekly?week_of={value}", headers=headers
            ).status_code
            == 422
        )


@pytest.mark.asyncio
async def test_weekly_tss_query_includes_monday_and_excludes_next_monday(monkeypatch):
    cursor = AsyncMock()
    cursor.fetchall.return_value = []
    connection = MagicMock()
    connection.cursor.return_value.__aenter__ = AsyncMock(return_value=cursor)
    pool = MagicMock()
    pool.connection.return_value.__aenter__ = AsyncMock(return_value=connection)
    monkeypatch.setattr(garmin, "garmin_pool", pool)
    assert (
        await garmin.fetch_weekly_tss_inputs(date(2026, 9, 21), date(2026, 9, 28)) == []
    )
    sql, parameters = cursor.execute.call_args.args
    assert "start_time >= %s AND start_time < %s" in sql
    assert "LIMIT" not in sql
    assert tuple(value.isoformat() for value in parameters) == (
        "2026-09-21T00:00:00",
        "2026-09-28T00:00:00",
    )


def test_activity_tss_uses_recorded_run_and_supplied_threshold(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    fetch = AsyncMock(
        return_value=ACTIVITY | {"moving_seconds": 3600, "distance_km": 12}
    )
    monkeypatch.setattr(garmin, "fetch_activity_summary", fetch)
    response = client.get(
        "/activities/123/tss?threshold_pace_seconds_per_km=300",
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 200
    assert response.json()["tss"] == 100
    assert response.json()["method"] == "running_pace_estimate"
    assert response.json()["duration_seconds"] == 3600
    fetch.assert_awaited_once_with("123")


def test_activity_tss_heart_rate_threshold(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        garmin, "fetch_activity_summary", AsyncMock(return_value=ACTIVITY)
    )
    response = client.get(
        "/activities/123/tss?threshold_heart_rate_bpm=157",
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 200
    assert response.json()["threshold"] == 157
    assert response.json()["intensity"] == 150
    assert response.json()["duration_seconds"] == 1800
    assert response.json()["tss"] == 40
    assert response.json()["method"] == "heart_rate_estimate"
    assert response.json()["intensity_unit"] == "bpm"
    monkeypatch.setattr(
        garmin,
        "fetch_activity_summary",
        AsyncMock(return_value=ACTIVITY | {"average_heart_rate_bpm": None}),
    )
    assert (
        client.get(
            "/activities/123/tss?threshold_heart_rate_bpm=157",
            headers={"Authorization": "Bearer token"},
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/activities/123/tss?threshold_heart_rate_bpm=0",
            headers={"Authorization": "Bearer token"},
        ).status_code
        == 422
    )


def test_activity_tss_cycling_requires_matching_recording_inputs(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        garmin,
        "fetch_activity_summary",
        AsyncMock(
            return_value=ACTIVITY | {"activity_type": "cycling", "moving_seconds": 0}
        ),
    )
    response = client.get(
        "/activities/123/tss",
        params={
            "ftp_watts": 250,
            "normalized_power_watts": 250,
            "duration_seconds": 7200,
        },
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 200
    assert response.json()["tss"] == 200
    assert response.json()["method"] == "cycling_power"
    assert response.json() == json.loads(
        (Path(__file__).parents[1] / "contracts/activity_tss.json").read_text()
    )


@pytest.mark.parametrize(
    "query",
    [
        "threshold_pace_seconds_per_km=0",
        "threshold_pace_seconds_per_km=-1",
        "threshold_pace_seconds_per_km=nan",
        "threshold_pace_seconds_per_km=inf",
        "threshold_pace_seconds_per_km=fast",
        "ftp_watts=250",
        "threshold_pace_seconds_per_km=300&duration_seconds=3600",
    ],
)
def test_activity_tss_rejects_invalid_thresholds(monkeypatch, query):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        garmin, "fetch_activity_summary", AsyncMock(return_value=ACTIVITY)
    )
    response = client.get(
        f"/activities/123/tss?{query}", headers={"Authorization": "Bearer token"}
    )
    assert response.status_code == 422


def test_activity_tss_defaults_to_saved_profile_threshold(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        garmin, "fetch_activity_summary", AsyncMock(return_value=ACTIVITY)
    )
    profile = AsyncMock(
        return_value={"name": "Runner", "threshold_heart_rate_bpm": 157}
    )
    monkeypatch.setattr(garmin, "fetch_profile", profile)
    response = client.get(
        "/activities/123/tss", headers={"Authorization": "Bearer token"}
    )
    assert response.status_code == 200
    assert response.json()["threshold"] == 157
    assert response.json()["tss"] == 40
    profile.return_value = {"name": "Runner", "threshold_heart_rate_bpm": 170}
    response = client.get(
        "/activities/123/tss", headers={"Authorization": "Bearer token"}
    )
    assert response.status_code == 200
    assert response.json()["threshold"] == 170
    assert response.json()["tss"] == 27.5


@pytest.mark.parametrize(
    "activity,status",
    [
        (None, 404),
        (ACTIVITY | {"activity_type": "swimming"}, 422),
        (ACTIVITY | {"moving_seconds": None}, 422),
        (ACTIVITY | {"distance_km": None}, 422),
    ],
)
def test_activity_tss_missing_activity_or_data(monkeypatch, activity, status):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        garmin, "fetch_activity_summary", AsyncMock(return_value=activity)
    )
    response = client.get(
        "/activities/123/tss?threshold_pace_seconds_per_km=300",
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == status


def test_syncs_and_reports_new_garmin_activities(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    fetch = AsyncMock(
        side_effect=[
            [{"activity_id": "123"}],
            [{"activity_id": "123"}, {"activity_id": "456"}],
        ]
    )
    sync = AsyncMock()
    monkeypatch.setattr(garmin, "fetch_activity_index", fetch)
    monkeypatch.setattr(garmin, "run_garmindb_sync", sync)

    response = client.post(
        "/activities/sync", headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 200
    assert response.json() == {"new_activities": 1, "total_activities": 2}
    sync.assert_awaited_once_with()


def test_running_predictions_use_summary_data_only(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    fetch = AsyncMock(
        return_value=[
            {
                "activity_id": "123",
                "started_at": ACTIVITY["started_at"],
                "distance_km": 10.0,
                "moving_seconds": 3000.0,
            }
        ]
    )
    monkeypatch.setattr(garmin, "fetch_running_prediction_inputs", fetch)

    response = client.get(
        "/activities/running/predictions",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["run_count"] == 1
    assert data["longest_run_km"] == 10.0
    assert data["model_status"] == "range"
    assert len(data["predictions"]) == 4
    assert data["basis"][0]["source_activity_id"] == "123"
    assert data["predictions"][1]["predicted_seconds"] is None
    assert (
        data["predictions"][1]["low_seconds"] == data["predictions"][1]["high_seconds"]
    )
    fetch.assert_awaited_once_with()


def test_lists_visualization_ready_activities(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    fetch = AsyncMock(return_value=[ACTIVITY])
    monkeypatch.setattr(garmin, "fetch_activities", fetch)

    response = client.get(
        "/activities",
        params={"activity_type": "running", "limit": 20, "offset": 40},
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    assert response.json()[0] == ACTIVITY | {"started_at": "2026-09-11T06:30:00Z"}
    fetch.assert_awaited_once_with("running", 20, 40)


def test_lists_lightweight_activity_index(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    fetch = AsyncMock(
        return_value=[
            {
                "activity_id": "123",
                "started_at": ACTIVITY["started_at"],
                "activity_type": "running",
                "name": "Morning Run",
            }
        ]
    )
    monkeypatch.setattr(garmin, "fetch_activity_index", fetch)

    response = client.get(
        "/activities/index", headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "activity_id": "123",
            "started_at": "2026-09-11T06:30:00Z",
            "activity_type": "running",
            "name": "Morning Run",
        }
    ]
    fetch.assert_awaited_once_with()


def test_returns_one_activity(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    detail = ACTIVITY | {
        "activity": {"activity_id": "123", "sport": "running", "distance": 5.0},
        "steps_activity": {"activity_id": "123", "steps": 5000},
        "cycle_activity": None,
        "climbing_activity": None,
        "paddle_activity": None,
        "laps": [{"activity_id": "123", "lap": 1}],
        "splits": [],
        "records": [{"activity_id": "123", "record": 1, "hr": 150}],
        "activity_devices": [{"activity_id": "123", "device_serial_number": 42}],
        "devices": [{"serial_number": 42, "product": "Watch"}],
        "device_info": [{"file_id": "123", "serial_number": 42}],
        "files": [{"id": "123", "name": "123_ACTIVITY.fit"}],
    }
    monkeypatch.setattr(garmin, "fetch_activity", AsyncMock(return_value=detail))

    response = client.get(
        "/activities/123",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    assert response.json()["average_pace_seconds_per_km"] == 348.0
    assert response.json()["activity"]["distance"] == 5.0
    assert response.json()["steps_activity"]["steps"] == 5000
    assert response.json()["records"][0]["hr"] == 150
    assert response.json()["devices"][0]["product"] == "Watch"
    assert response.json()["files"][0]["id"] == "123"


def test_returns_only_activity_summary(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    fetch_summary = AsyncMock(return_value=ACTIVITY)
    fetch_detail = AsyncMock()
    monkeypatch.setattr(garmin, "fetch_activity_summary", fetch_summary)
    monkeypatch.setattr(garmin, "fetch_activity", fetch_detail)

    response = client.get(
        "/activities/123/summary",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    assert response.json() == ACTIVITY | {"started_at": "2026-09-11T06:30:00Z"}
    fetch_summary.assert_awaited_once_with("123")
    fetch_detail.assert_not_awaited()


def test_unknown_activity_summary_returns_not_found(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(garmin, "fetch_activity_summary", AsyncMock(return_value=None))

    response = client.get(
        "/activities/missing/summary",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found."}


def test_unknown_activity_returns_not_found(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(garmin, "fetch_activity", AsyncMock(return_value=None))

    response = client.get(
        "/activities/missing",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found."}
