from unittest.mock import Mock

import pytest
import requests

from weather_score.weather.providers import openmeteo


@pytest.mark.asyncio
async def test_returns_elevation(monkeypatch):
    response = Mock()
    response.json.return_value = {"elevation": [42.0]}
    get = Mock(return_value=response)
    monkeypatch.setattr(openmeteo.requests, "get", get)

    result = await openmeteo.get_openmeteo_altitude("-27.47", "153.03")

    assert result == {"elevation": [42.0]}
    get.assert_called_once_with(
        "https://api.open-meteo.com/v1/elevation?latitude=-27.47&longitude=153.03",
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()


@pytest.mark.asyncio
async def test_propagates_http_errors(monkeypatch):
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("bad gateway")
    monkeypatch.setattr(openmeteo.requests, "get", Mock(return_value=response))

    with pytest.raises(requests.HTTPError, match="bad gateway"):
        await openmeteo.get_openmeteo_altitude("-27.47", "153.03")


@pytest.mark.asyncio
async def test_propagates_timeouts(monkeypatch):
    monkeypatch.setattr(
        openmeteo.requests,
        "get",
        Mock(side_effect=requests.Timeout("timed out")),
    )

    with pytest.raises(requests.Timeout, match="timed out"):
        await openmeteo.get_openmeteo_altitude("-27.47", "153.03")


@pytest.mark.asyncio
async def test_propagates_invalid_json(monkeypatch):
    response = Mock()
    response.json.side_effect = requests.JSONDecodeError("invalid", "", 0)
    monkeypatch.setattr(openmeteo.requests, "get", Mock(return_value=response))

    with pytest.raises(requests.JSONDecodeError):
        await openmeteo.get_openmeteo_altitude("-27.47", "153.03")


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [None, {}, {"elevation": None}])
async def test_rejects_malformed_elevation(monkeypatch, data):
    response = Mock()
    response.json.return_value = data
    monkeypatch.setattr(openmeteo.requests, "get", Mock(return_value=response))

    with pytest.raises(TypeError, match="invalid elevation data"):
        await openmeteo.get_openmeteo_altitude("-27.47", "153.03")
