import importlib
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test")

main = importlib.import_module("apps.api.main")
auth = importlib.import_module("apps.api.security.auth")
routes = importlib.import_module("apps.api.routes.profile")
service = importlib.import_module("apps.api.services.profile")
client = TestClient(main.app, raise_server_exceptions=False)


def test_profile_requires_authentication():
    assert client.get("/profile").status_code == 401
    assert (
        client.put(
            "/profile", json={"name": "Runner", "threshold_heart_rate_bpm": 157}
        ).status_code
        == 401
    )


def test_reads_initial_profile_and_saves_validated_values(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        routes,
        "fetch_profile",
        AsyncMock(return_value={"name": None, "threshold_heart_rate_bpm": 157}),
    )
    headers = {"Authorization": "Bearer token"}
    assert client.get("/profile", headers=headers).json() == {
        "name": None,
        "threshold_heart_rate_bpm": 157,
    }
    save = AsyncMock(return_value={"name": "Runner", "threshold_heart_rate_bpm": 160})
    monkeypatch.setattr(routes, "save_profile", save)
    response = client.put(
        "/profile",
        headers=headers,
        json={"name": " Runner ", "threshold_heart_rate_bpm": 160},
    )
    assert response.status_code == 200
    assert response.json() == {"name": "Runner", "threshold_heart_rate_bpm": 160}
    save.assert_awaited_once_with("Runner", 160)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": " ", "threshold_heart_rate_bpm": 157},
        {"name": "x" * 101, "threshold_heart_rate_bpm": 157},
        {"name": "Runner", "threshold_heart_rate_bpm": 157, "id": 2},
    ]
    + [
        {"name": "Runner", "threshold_heart_rate_bpm": value}
        for value in (None, 0, 29, 251, 157.5, True, "157")
    ],
)
def test_profile_rejects_invalid_input_without_saving(monkeypatch, payload):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    save = AsyncMock()
    monkeypatch.setattr(routes, "save_profile", save)
    response = client.put(
        "/profile", headers={"Authorization": "Bearer token"}, json=payload
    )
    assert response.status_code == 422
    save.assert_not_awaited()


@pytest.mark.asyncio
async def test_profile_persistence_uses_parameterized_upsert_and_preserves_defaults(
    monkeypatch,
):
    cursor = AsyncMock()
    cursor.fetchone.return_value = {"name": "Runner", "threshold_heart_rate_bpm": 160}
    connection = MagicMock()
    connection.cursor.return_value.__aenter__ = AsyncMock(return_value=cursor)
    pool = MagicMock()
    pool.connection.return_value.__aenter__ = AsyncMock(return_value=connection)
    monkeypatch.setattr(service, "pool", pool)
    assert await service.save_profile("Runner", 160) == cursor.fetchone.return_value
    query, values = cursor.execute.call_args.args
    assert "ON CONFLICT (id) DO UPDATE" in query
    assert values == ("Runner", 160)
    cursor.reset_mock()
    assert await service.fetch_profile() == cursor.fetchone.return_value
    assert "ON CONFLICT (id) DO NOTHING" in cursor.execute.call_args_list[1].args[0]
    assert "DEFAULT 157" in service.CREATE_PROFILE
    assert "CHECK (id = 1)" in service.CREATE_PROFILE
