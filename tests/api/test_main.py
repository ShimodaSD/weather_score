import importlib
import json
import os
from pathlib import Path
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
geocoding = importlib.import_module("apps.api.services.geocoding")
scoring = importlib.import_module("apps.api.services.scoring")
location_schemas = importlib.import_module("apps.api.schemas.location")


client = TestClient(main.app, raise_server_exceptions=False)


def response_with(data):
    response = Mock()
    response.json.return_value = data
    return response


def test_root_returns_service_status():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_address_is_required():
    response = client.get("/address-to-lat-long")

    assert response.status_code == 422


def test_old_score_run_route_is_gone():
    assert client.get("/score/run", params={"address": "Brisbane"}).status_code == 404


def test_geocodes_address(monkeypatch):
    get = Mock(return_value=response_with([{"lat": "-27.47", "lon": "153.03"}]))
    monkeypatch.setattr(geocoding.requests, "get", get)

    response = client.get("/address-to-lat-long", params={"address": "Brisbane"})

    assert response.status_code == 200
    assert response.json() == {"latitude": "-27.47", "longitude": "153.03"}
    get.assert_called_once()


def test_ambiguous_address_returns_options_without_fetching_weather(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    options = [
        {
            "display_name": "Springfield, Queensland",
            "lat": "-24.92",
            "lon": "152.32",
        },
        {
            "display_name": "Springfield, Victoria",
            "lat": "-37.41",
            "lon": "144.82",
        },
    ]
    monkeypatch.setattr(
        geocoding.requests,
        "get",
        Mock(return_value=response_with(options)),
    )
    get_weather = AsyncMock()
    monkeypatch.setattr(scoring, "fetch_current_weather", get_weather)

    response = client.post(
        "/grade/run",
        params={"address": "Springfield"},
        headers={"Authorization": "Bearer token"},
        json={"average_pace_minutes_per_km": "5:20"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "options": [
            {
                "name": "Springfield, Queensland",
                "latitude": "-24.92",
                "longitude": "152.32",
            },
            {
                "name": "Springfield, Victoria",
                "latitude": "-37.41",
                "longitude": "144.82",
            },
        ]
    }
    get_weather.assert_not_awaited()


def test_unknown_address_returns_error(monkeypatch):
    monkeypatch.setattr(
        geocoding.requests,
        "get",
        Mock(return_value=response_with([])),
    )

    response = client.get("/address-to-lat-long", params={"address": "Unknown"})

    assert response.status_code == 200
    assert response.json() == {"error": "Address not found"}


def test_geocoding_failure_returns_bad_gateway(monkeypatch):
    monkeypatch.setattr(
        geocoding.requests,
        "get",
        Mock(side_effect=requests.Timeout("timed out")),
    )

    response = client.get("/address-to-lat-long", params={"address": "Brisbane"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Could not retrieve coordinates."}


def test_score_run_by_type_uses_training_type(monkeypatch):
    monkeypatch.setattr(
        scoring,
        "geocode_address",
        AsyncMock(
            return_value=location_schemas.CoordinatesResponse(
                latitude="-27.47",
                longitude="153.03",
            )
        ),
    )
    weather = {"current": {"temp_c": 7}}
    altitude = {"elevation": [10]}
    monkeypatch.setattr(
        scoring, "fetch_current_weather", AsyncMock(return_value=weather)
    )
    monkeypatch.setattr(
        scoring, "fetch_elevation", AsyncMock(return_value=altitude)
    )
    calculate_score_by_type = AsyncMock(return_value=99)
    monkeypatch.setattr(
        scoring,
        "calculate_activity_score_by_training_type",
        calculate_score_by_type,
    )

    response = client.get(
        "/score/run/by-type",
        params={"address": "Brisbane", "training_type": "easy"},
    )

    assert response.status_code == 200
    assert response.json() == 99
    calculate_score_by_type.assert_awaited_once_with(weather, altitude, "easy")


def test_score_run_by_type_rejects_unknown_type():
    response = client.get(
        "/score/run/by-type",
        params={"address": "Brisbane", "training_type": "recovery"},
    )

    assert response.status_code == 422


def test_grade_run_is_public(monkeypatch):
    monkeypatch.setattr(scoring, "geocode_address", AsyncMock(return_value=None))

    response = client.post(
        "/grade/run",
        params={"address": "Brisbane"},
        json={
            "average_pace_minutes_per_km": 5,
        },
    )

    assert response.status_code == 200


def test_grade_run_returns_factor_breakdown(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        scoring,
        "geocode_address",
        AsyncMock(
            return_value=location_schemas.CoordinatesResponse(
                latitude=" -27.47 ",
                longitude=" 153.03 ",
            )
        ),
    )
    get_weather = AsyncMock(
        return_value={"current": {"gust_kph": 12, "wetbulb_c": 15}}
    )
    monkeypatch.setattr(scoring, "fetch_current_weather", get_weather)

    response = client.post(
        "/grade/run",
        params={"address": "Brisbane"},
        headers={"Authorization": "Bearer token"},
        json={
            "average_pace_minutes_per_km": "5:20",
        },
    )

    assert response.status_code == 200
    contract = Path(__file__).parents[1] / "contracts" / "run_grade.json"
    assert response.json() == json.loads(contract.read_text())
    get_weather.assert_awaited_once_with("-27.47", "153.03")


def test_grade_run_uses_selected_coordinates(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    geocode = AsyncMock()
    monkeypatch.setattr(scoring, "geocode_address", geocode)
    get_weather = AsyncMock(return_value={"current": {"gust_kph": 12, "wetbulb_c": 15}})
    monkeypatch.setattr(scoring, "fetch_current_weather", get_weather)

    response = client.post(
        "/grade/run",
        params={"address": "Springfield", "latitude": -37.41, "longitude": 144.82},
        headers={"Authorization": "Bearer token"},
        json={"average_pace_minutes_per_km": "5:20"},
    )

    assert response.status_code == 200
    assert response.json()["score"] == 96.53
    geocode.assert_not_awaited()
    get_weather.assert_awaited_once_with("-37.41", "144.82")


@pytest.mark.parametrize(
    "coordinates", [{"latitude": -37.41}, {"latitude": 91, "longitude": 144.82}]
)
def test_grade_run_rejects_invalid_coordinates(monkeypatch, coordinates):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    response = client.post(
        "/grade/run",
        params={"address": "Springfield", **coordinates},
        headers={"Authorization": "Bearer token"},
        json={"average_pace_minutes_per_km": "5:20"},
    )
    assert response.status_code == 422


def test_grade_run_rejects_missing_pace(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")

    response = client.post(
        "/grade/run",
        params={"address": "Brisbane"},
        headers={"Authorization": "Bearer token"},
        json={},
    )

    assert response.status_code == 422


def test_grade_run_requires_address(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")

    response = client.post(
        "/grade/run",
        headers={"Authorization": "Bearer token"},
        json={"average_pace_minutes_per_km": 5},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("pace", ["5:60", "5.20", "five minutes"])
def test_grade_run_rejects_invalid_pace_format(monkeypatch, pace):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")

    response = client.post(
        "/grade/run",
        params={"address": "Brisbane"},
        headers={"Authorization": "Bearer token"},
        json={"average_pace_minutes_per_km": pace},
    )

    assert response.status_code == 422


def test_grade_run_rejects_client_supplied_weather(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")

    response = client.post(
        "/grade/run",
        params={"address": "Brisbane"},
        headers={"Authorization": "Bearer token"},
        json={
            "average_pace_minutes_per_km": 5,
            "headwind_kph": 12,
        },
    )

    assert response.status_code == 422


def test_grade_run_stops_when_address_is_not_found(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(scoring, "geocode_address", AsyncMock(return_value=None))
    get_weather = AsyncMock()
    monkeypatch.setattr(scoring, "fetch_current_weather", get_weather)

    response = client.post(
        "/grade/run",
        params={"address": "Unknown"},
        headers={"Authorization": "Bearer token"},
        json={"average_pace_minutes_per_km": 5},
    )

    assert response.status_code == 200
    assert response.json() == {
        "error": "Could not retrieve latitude and longitude for the given address."
    }
    get_weather.assert_not_awaited()


def test_grade_run_provider_failure_returns_bad_gateway(monkeypatch):
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    monkeypatch.setattr(
        scoring,
        "geocode_address",
        AsyncMock(
            return_value=location_schemas.CoordinatesResponse(
                latitude="-27.47",
                longitude="153.03",
            )
        ),
    )
    monkeypatch.setattr(
        scoring,
        "fetch_current_weather",
        AsyncMock(return_value={"current": {"gust_kph": 12}}),
    )

    response = client.post(
        "/grade/run",
        params={"address": "Brisbane"},
        headers={"Authorization": "Bearer token"},
        json={"average_pace_minutes_per_km": 5},
    )

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


def test_browser_session_expires_after_one_day_and_logout_clears_it(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_USERNAME", "runner")
    monkeypatch.setattr(auth, "AUTH_PASSWORD", "secret")
    monkeypatch.setattr(auth, "ACCESS_TOKEN", "token")
    now = 1_000_000
    monkeypatch.setattr(auth.time, "time", lambda: now)
    browser = TestClient(main.app, raise_server_exceptions=False)

    login = browser.post("/token", data={"username": "runner", "password": "secret"})
    assert login.status_code == 200
    assert "Max-Age=86400" in login.headers["set-cookie"]
    assert "httponly" in login.headers["set-cookie"].lower()
    assert browser.get("/session").json() == {"authenticated": True}
    assert browser.post("/grade/run").status_code == 422

    assert browser.post("/logout").status_code == 204
    assert browser.get("/session").status_code == 401

    browser.post("/token", data={"username": "runner", "password": "secret"})
    now += auth.SESSION_SECONDS
    assert browser.get("/session").status_code == 401
    assert browser.get("/activities/index").status_code == 401


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
