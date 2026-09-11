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
