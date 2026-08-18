import os

import weatherapi

config = weatherapi.Configuration()
config.api_key["key"] = os.environ.get("WEATHER_API_KEY")
instance = weatherapi.APIsApi(weatherapi.ApiClient(config))


async def get_weatherapi_lat_long(latitude: str | None, longitude: str | None):
    try:
        return instance.realtime_weather(f"{latitude},{longitude}")
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None
