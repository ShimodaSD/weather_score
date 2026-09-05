import importlib
import os
from unittest.mock import AsyncMock, Mock

import pytest
import requests
from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test")

main = importlib.import_module("apps.api.main")
auth = importlib.import_module("apps.api.security.auth")


client = TestClient(main.app, raise_server_exceptions=False)


def response_with(data):
    response = Mock()
    response.json.return_value = data
    return response


def test_root_returns_service_status():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "running"}


@pytest.mark.parametrize("path", ["/address-to-lat-long", "/score/run"])
def test_address_is_required(path):
    response = client.get(path)

    assert response.status_code == 422


def test_geocodes_address(monkeypatch):
    get = Mock(return_value=response_with([{"lat": "-27.47", "lon": "153.03"}]))
    monkeypatch.setattr(main.requests, "get", get)

    response = client.get("/address-to-lat-long", params={"address": "Brisbane"})

    assert response.status_code == 200
    assert response.json() == {"latitude": "-27.47", "longitude": "153.03"}
    get.assert_called_once()


def test_unknown_address_returns_error(monkeypatch):
    monkeypatch.setattr(main.requests, "get", Mock(return_value=response_with([])))

    response = client.get("/address-to-lat-long", params={"address": "Unknown"})

    assert response.status_code == 200
    assert response.json() == {"error": "Address not found"}


def test_geocoding_failure_returns_bad_gateway(monkeypatch):
    monkeypatch.setattr(
        main.requests, "get", Mock(side_effect=requests.Timeout("timed out"))
    )

    response = client.get("/address-to-lat-long", params={"address": "Brisbane"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Could not retrieve coordinates."}


def test_score_run_calls_services(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_lat_long",
        AsyncMock(return_value={"latitude": " -27.47 ", "longitude": " 153.03 "}),
    )
    weather = {"current": {"temp_c": 7}}
    altitude = {"elevation": [10]}
    get_weather = AsyncMock(return_value=weather)
    get_altitude = AsyncMock(return_value=altitude)
    generate_grade = AsyncMock(return_value=98.5)
    monkeypatch.setattr(main, "get_weatherapi_lat_long", get_weather)
    monkeypatch.setattr(main, "get_openmeteo_altitude", get_altitude)
    monkeypatch.setattr(main, "generate_grade", generate_grade)

    response = client.get("/score/run", params={"address": "Brisbane"})

    assert response.status_code == 200
    assert response.json() == 98.5
    get_weather.assert_awaited_once_with("-27.47", "153.03")
    get_altitude.assert_awaited_once_with("-27.47", "153.03")
    generate_grade.assert_awaited_once_with(weather, altitude)


def test_score_run_stops_when_address_is_not_found(monkeypatch):
    monkeypatch.setattr(main, "get_lat_long", AsyncMock(return_value={"error": "not found"}))
    get_weather = AsyncMock()
    monkeypatch.setattr(main, "get_weatherapi_lat_long", get_weather)

    response = client.get("/score/run", params={"address": "Unknown"})

    assert response.status_code == 200
    assert response.json() == {
        "error": "Could not retrieve latitude and longitude for the given address."
    }
    get_weather.assert_not_awaited()


def test_score_run_provider_failure_returns_bad_gateway(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_lat_long",
        AsyncMock(return_value={"latitude": "-27.47", "longitude": "153.03"}),
    )
    monkeypatch.setattr(
        main, "get_weatherapi_lat_long", AsyncMock(side_effect=TimeoutError("timeout"))
    )
    monkeypatch.setattr(main, "get_openmeteo_altitude", AsyncMock(return_value={}))

    response = client.get("/score/run", params={"address": "Brisbane"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Could not retrieve weather data."}


def test_login_returns_access_token(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_USERNAME", "runner")
    monkeypatch.setattr(auth, "AUTH_PASSWORD", "secret")
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")

    response = client.post(
        "/token", data={"username": "runner", "password": "secret"}
    )

    assert response.status_code == 200
    assert response.json() == {"access_token": "token", "token_type": "bearer"}


def test_login_rejects_incorrect_credentials(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_USERNAME", "runner")
    monkeypatch.setattr(auth, "AUTH_PASSWORD", "secret")

    response = client.post(
        "/token", data={"username": "runner", "password": "wrong"}
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_requires_form_fields():
    response = client.post("/token", data={})

    assert response.status_code == 422
