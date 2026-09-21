import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from numbers import Real

import weatherapi

config = weatherapi.Configuration()
config.api_key["key"] = os.environ.get("WEATHER_API_KEY")
instance = weatherapi.APIsApi(weatherapi.ApiClient(config))


@dataclass(frozen=True, slots=True)
class HistoricalConditions:
    """Normalized historical inputs used by the scoring engine."""

    gust_kph: float | None
    wind_degree: float
    wind_kph: float
    temperature_c: float
    humidity_percent: float
    uv_index: float
    cloud_percent: float
    weather_at: datetime


async def fetch_current_weather(latitude: str, longitude: str) -> dict:
    if not latitude or not longitude:
        raise ValueError("Latitude and longitude are required.")

    weather = await asyncio.to_thread(
        instance.realtime_weather, f"{latitude},{longitude}"
    )
    if not isinstance(weather, dict) or not isinstance(weather.get("current"), dict):
        raise TypeError("WeatherAPI returned invalid weather data.")
    return weather


async def fetch_historical_conditions(
    latitude: float, longitude: float, recorded_at: datetime
) -> HistoricalConditions:
    """Return historical weather from the hour closest to a Garmin timestamp."""
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Latitude or longitude is out of range.")
    target = recorded_at.replace(tzinfo=None, second=0, microsecond=0) + timedelta(
        minutes=30
    )
    target = target.replace(minute=0)
    weather = await asyncio.to_thread(
        instance.history_weather,
        f"{latitude},{longitude}",
        target.date().isoformat(),
        hour=target.hour,
    )
    forecast = weather.get("forecast") if isinstance(weather, dict) else None
    days = forecast.get("forecastday") if isinstance(forecast, dict) else None
    hours = [
        hour
        for day in days or []
        if isinstance(day, dict) and isinstance(day.get("hour"), list)
        for hour in day["hour"]
        if isinstance(hour, dict)
    ]
    if not hours:
        raise TypeError("WeatherAPI returned invalid historical data.")
    hour = min(
        hours,
        key=lambda item: abs((_time(item) - target).total_seconds()),
    )
    return HistoricalConditions(
        gust_kph=_optional_number(hour, "gust_kph", minimum=0),
        wind_degree=_number(hour, "wind_degree", minimum=0, maximum=360),
        wind_kph=_number(hour, "wind_kph", minimum=0),
        temperature_c=_number(hour, "temp_c", minimum=-50, maximum=60),
        humidity_percent=_number(hour, "humidity", minimum=0, maximum=100),
        uv_index=_number(hour, "uv", minimum=0),
        cloud_percent=_number(hour, "cloud", minimum=0, maximum=100),
        weather_at=_time(hour),
    )


def _time(data: dict[str, object]) -> datetime:
    value = data.get("time")
    if not isinstance(value, str):
        raise TypeError("Historical weather time must be a string.")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Historical weather time is invalid.") from error


def _number(
    data: dict[str, object],
    name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = data.get(name)
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"Weather {name} must be a number.")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"Weather {name} must be finite.")
    if (
        minimum is not None
        and number < minimum
        or maximum is not None
        and number > maximum
    ):
        raise ValueError(f"Weather {name} is out of range.")
    return number


def _optional_number(
    data: dict[str, object],
    name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    if data.get(name) is None:
        return None
    return _number(data, name, minimum, maximum)
