import asyncio
import os

import weatherapi

config = weatherapi.Configuration()
config.api_key["key"] = os.environ.get("WEATHER_API_KEY")
instance = weatherapi.APIsApi(weatherapi.ApiClient(config))


async def get_weatherapi_lat_long(latitude: str, longitude: str) -> dict:
    if not latitude or not longitude:
        raise ValueError("Latitude and longitude are required.")

    weather = await asyncio.to_thread(
        instance.realtime_weather, f"{latitude},{longitude}"
    )
    if not isinstance(weather, dict) or not isinstance(weather.get("current"), dict):
        raise TypeError("WeatherAPI returned invalid weather data.")
    return weather
