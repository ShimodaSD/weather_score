import importlib
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from weather_score.weather.providers.weather_api import HistoricalConditions

os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test")

main = importlib.import_module("apps.api.main")
auth = importlib.import_module("apps.api.security.auth")
garmin = importlib.import_module("apps.api.routes.garmin")
activity_grades = importlib.import_module("apps.api.services.activity_grades")

client = TestClient(main.app, raise_server_exceptions=False)
NOW = datetime(2026, 9, 17, tzinfo=UTC)
PROCESSING = {
    "activity_id": "123",
    "status": "processing",
    "score": None,
    "segments": [],
    "error": None,
    "created_at": NOW,
    "updated_at": NOW,
    "completed_at": None,
}


def test_activity_grade_endpoints_require_bearer_token():
    assert client.get("/activities/grades").status_code == 401
    assert client.post("/activities/123/grade").status_code == 401


def test_starts_grade_with_200_and_runs_background_processing(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        garmin,
        "fetch_activity_summary",
        AsyncMock(return_value={"activity_id": "123", "activity_type": "running"}),
    )
    queue = AsyncMock(return_value=PROCESSING)
    process = AsyncMock()
    monkeypatch.setattr(garmin, "queue_activity_grade", queue)
    monkeypatch.setattr(garmin, "process_activity_grade", process)

    response = client.post(
        "/activities/123/grade", headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    queue.assert_awaited_once_with("123")
    process.assert_awaited_once_with("123")


def test_lists_persisted_activity_grades(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    fetch = AsyncMock(return_value=[PROCESSING])
    monkeypatch.setattr(garmin, "fetch_activity_grades", fetch)

    response = client.get(
        "/activities/grades", headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 200
    assert response.json()[0]["activity_id"] == "123"
    fetch.assert_awaited_once_with()


def test_unknown_activity_is_not_queued(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(garmin, "fetch_activity_summary", AsyncMock(return_value=None))
    queue = AsyncMock()
    monkeypatch.setattr(garmin, "queue_activity_grade", queue)

    response = client.post(
        "/activities/missing/grade", headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 404
    queue.assert_not_awaited()


def test_non_running_activity_is_not_queued(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        garmin,
        "fetch_activity_summary",
        AsyncMock(return_value={"activity_id": "123", "activity_type": "cycling"}),
    )
    queue = AsyncMock()
    monkeypatch.setattr(garmin, "queue_activity_grade", queue)

    response = client.post(
        "/activities/123/grade", headers={"Authorization": "Bearer token"}
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Only running activities can be graded."}
    queue.assert_not_awaited()


@pytest.mark.asyncio
async def test_processor_grades_each_200_metres_and_persists_average(monkeypatch):
    records = [
        {
            "distance": distance,
            "timestamp": datetime.fromtimestamp(seconds, tz=UTC),
            "position_lat": -27.47,
            "position_long": 153.03,
        }
        for distance, seconds in ((0, 0), (0.2, 60), (0.4, 120))
    ]
    history = AsyncMock(
        return_value=HistoricalConditions(
            gust_kph=None,
            wind_degree=0,
            wind_kph=8,
            temperature_c=24,
            humidity_percent=60,
            uv_index=4,
            cloud_percent=20,
            weather_at=datetime(2026, 9, 17, tzinfo=UTC),
        )
    )
    complete = AsyncMock()
    failed = AsyncMock()
    monkeypatch.setattr(
        activity_grades,
        "_fetch_activity_records",
        AsyncMock(return_value=records),
    )
    monkeypatch.setattr(activity_grades, "fetch_historical_conditions", history)
    monkeypatch.setattr(activity_grades, "_complete_activity_grade", complete)
    monkeypatch.setattr(activity_grades, "_fail_activity_grade", failed)

    await activity_grades.process_activity_grade("123")

    assert history.await_count == 2
    first_time = history.await_args_list[0].args[2]
    second_time = history.await_args_list[1].args[2]
    assert (second_time - first_time).total_seconds() == 60
    activity_id, score, segments = complete.await_args.args
    assert activity_id == "123"
    assert 0 <= score <= 100
    assert [segment["end_distance_m"] for segment in segments] == [200, 400]
    assert [segment["headwind_kph"] for segment in segments] == [8, 8]
    assert [segment["wind_kph"] for segment in segments] == [8, 8]
    assert all(segment["wbgt_c"] > 0 for segment in segments)
    failed.assert_not_awaited()
