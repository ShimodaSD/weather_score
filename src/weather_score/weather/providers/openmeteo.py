import requests


async def get_openmeteo_altitude(lat: str, lon: str) -> dict:
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"
    response = requests.get(url)
    return response.json()
