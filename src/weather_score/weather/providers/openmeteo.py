import asyncio

import requests


async def fetch_elevation(latitude: str, longitude: str) -> dict:
    url = f"https://api.open-meteo.com/v1/elevation?latitude={latitude}&longitude={longitude}"
    response = await asyncio.to_thread(requests.get, url, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get("elevation"), list):
        raise TypeError("Open-Meteo returned invalid elevation data.")
    return data


async def fetch_weather_forecast(latitude: str, longitude: str) -> dict:
    response = await asyncio.to_thread(
        requests.get,
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum,wind_gusts_10m_max",
            "forecast_days": 7,
            "timezone": "auto",
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    daily = data.get("daily") if isinstance(data, dict) else None
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        raise TypeError("Open-Meteo returned invalid forecast data.")
    fields = ("temperature_2m_mean", "relative_humidity_2m_mean", "precipitation_sum", "wind_gusts_10m_max")
    if any(not isinstance(daily.get(field), list) or len(daily[field]) != len(daily["time"]) for field in fields):
        raise TypeError("Open-Meteo returned incomplete forecast data.")
    return data
