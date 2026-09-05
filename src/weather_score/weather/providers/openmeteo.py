import asyncio

import requests


async def get_openmeteo_altitude(lat: str, lon: str) -> dict:
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"
    response = await asyncio.to_thread(requests.get, url, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get("elevation"), list):
        raise TypeError("Open-Meteo returned invalid elevation data.")
    return data
