from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from weather_score.weather.providers import weather_api


@pytest.mark.asyncio
async def test_returns_weather_for_coordinates(monkeypatch):
    realtime_weather = Mock(return_value={"current": {"temp_c": 20}})
    monkeypatch.setattr(weather_api.instance, "realtime_weather", realtime_weather)

    result = await weather_api.fetch_current_weather("-27.47", "153.03")

    assert result == {"current": {"temp_c": 20}}
    realtime_weather.assert_called_once_with("-27.47,153.03")


@pytest.mark.asyncio
async def test_propagates_provider_errors(monkeypatch):
    realtime_weather = Mock(side_effect=TimeoutError("timed out"))
    monkeypatch.setattr(weather_api.instance, "realtime_weather", realtime_weather)

    with pytest.raises(TimeoutError, match="timed out"):
        await weather_api.fetch_current_weather("-27.47", "153.03")


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [None, {}, {"current": None}])
async def test_rejects_malformed_weather(monkeypatch, response):
    monkeypatch.setattr(
        weather_api.instance, "realtime_weather", Mock(return_value=response)
    )

    with pytest.raises(TypeError, match="invalid weather data"):
        await weather_api.fetch_current_weather("-27.47", "153.03")


@pytest.mark.asyncio
async def test_rejects_missing_coordinates():
    with pytest.raises(ValueError, match="required"):
        await weather_api.fetch_current_weather("", "153.03")


@pytest.mark.asyncio
async def test_returns_history_hour_closest_to_recorded_minute(monkeypatch):
    history_weather = Mock(
        return_value={
            "forecast": {
                "forecastday": [
                    {
                        "hour": [
                            {
                                "time": "2026-09-11 15:00",
                                "gust_kph": 10,
                                "wind_degree": 90,
                                "wind_kph": 6,
                                "temp_c": 18,
                                "humidity": 70,
                                "uv": 1,
                                "cloud": 50,
                                "wetbulb_c": 12,
                            },
                            {
                                "time": "2026-09-11 16:00",
                                "wind_degree": 180,
                                "wind_kph": 12,
                                "temp_c": 24,
                                "humidity": 60,
                                "uv": 4,
                                "cloud": 20,
                                "wetbulb_c": 14,
                            },
                        ]
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(weather_api.instance, "history_weather", history_weather)

    result = await weather_api.fetch_historical_conditions(
        -27.47, 153.03, datetime(2026, 9, 11, 15, 36, tzinfo=UTC)
    )

    assert result.gust_kph is None
    assert result.wind_degree == 180
    assert result.wind_kph == 12
    assert result.temperature_c == 24
    assert result.humidity_percent == 60
    assert result.weather_at == datetime(2026, 9, 11, 16, tzinfo=UTC).replace(
        tzinfo=None
    )
    history_weather.assert_called_once_with("-27.47,153.03", "2026-09-11", hour=16)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [None, {}, {"forecast": {}}, {"forecast": {"forecastday": []}}],
)
async def test_rejects_malformed_history(monkeypatch, response):
    monkeypatch.setattr(
        weather_api.instance, "history_weather", Mock(return_value=response)
    )

    with pytest.raises(TypeError, match="invalid historical data"):
        await weather_api.fetch_historical_conditions(-27.47, 153.03, datetime.now(UTC))


@pytest.mark.asyncio
async def test_rejects_out_of_range_historical_values(monkeypatch):
    monkeypatch.setattr(
        weather_api.instance,
        "history_weather",
        Mock(
            return_value={
                "forecast": {
                    "forecastday": [
                        {
                            "hour": [
                                {
                                    "time": "2026-09-11 15:00",
                                    "gust_kph": -1,
                                    "wind_degree": 90,
                                    "wind_kph": 6,
                                    "temp_c": 18,
                                    "humidity": 70,
                                    "uv": 1,
                                    "cloud": 50,
                                }
                            ]
                        }
                    ]
                }
            }
        ),
    )

    with pytest.raises(ValueError, match="out of range"):
        await weather_api.fetch_historical_conditions(-27.47, 153.03, datetime.now(UTC))
