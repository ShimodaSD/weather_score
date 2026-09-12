import importlib
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock

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
    assert client.get("/activities/123/summary").status_code == 401
    assert client.get("/activities/running/predictions").status_code == 401


def test_running_predictions_use_summary_data_only(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    fetch = AsyncMock(return_value=[{
        "activity_id": "123",
        "started_at": ACTIVITY["started_at"],
        "distance_km": 10.0,
        "moving_seconds": 3000.0,
    }])
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
    assert data["predictions"][1]["low_seconds"] == data["predictions"][1]["high_seconds"]
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
    fetch = AsyncMock(return_value=[{
        "activity_id": "123",
        "started_at": ACTIVITY["started_at"],
        "activity_type": "running",
        "name": "Morning Run",
    }])
    monkeypatch.setattr(garmin, "fetch_activity_index", fetch)

    response = client.get("/activities/index", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json() == [{
        "activity_id": "123",
        "started_at": "2026-09-11T06:30:00Z",
        "activity_type": "running",
        "name": "Morning Run",
    }]
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
