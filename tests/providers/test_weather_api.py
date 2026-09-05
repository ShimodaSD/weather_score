from unittest.mock import Mock

import pytest

from weather_score.weather.providers import weather_api


@pytest.mark.asyncio
async def test_returns_weather_for_coordinates(monkeypatch):
    realtime_weather = Mock(return_value={"current": {"temp_c": 20}})
    monkeypatch.setattr(weather_api.instance, "realtime_weather", realtime_weather)

    result = await weather_api.get_weatherapi_lat_long("-27.47", "153.03")

    assert result == {"current": {"temp_c": 20}}
    realtime_weather.assert_called_once_with("-27.47,153.03")


@pytest.mark.asyncio
async def test_propagates_provider_errors(monkeypatch):
    realtime_weather = Mock(side_effect=TimeoutError("timed out"))
    monkeypatch.setattr(weather_api.instance, "realtime_weather", realtime_weather)

    with pytest.raises(TimeoutError, match="timed out"):
        await weather_api.get_weatherapi_lat_long("-27.47", "153.03")


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [None, {}, {"current": None}])
async def test_rejects_malformed_weather(monkeypatch, response):
    monkeypatch.setattr(
        weather_api.instance, "realtime_weather", Mock(return_value=response)
    )

    with pytest.raises(TypeError, match="invalid weather data"):
        await weather_api.get_weatherapi_lat_long("-27.47", "153.03")


@pytest.mark.asyncio
async def test_rejects_missing_coordinates():
    with pytest.raises(ValueError, match="required"):
        await weather_api.get_weatherapi_lat_long("", "153.03")
