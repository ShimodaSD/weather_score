from contextlib import asynccontextmanager

import requests
import uvicorn
from fastapi import APIRouter, Depends, FastAPI

try:
    from ...src.grade_weather.main import generate_grade
    from ...src.weather_score.weather.providers.weather_api import (
        get_weatherapi_lat_long,
    )
    from .database import pool
    from .security import require_access_token, security_router
except ImportError:
    from database import pool
    from security import require_access_token, security_router
    from src.grade_weather.main import generate_grade

    from src.weather_score.weather.providers.weather_api import get_weatherapi_lat_long


@asynccontextmanager
async def lifespan(_: FastAPI):
    await pool.open()
    try:
        yield
    finally:
        await pool.close()


openapi_tags = [
    {"name": "System", "description": "Health and service status endpoints."},
    {"name": "Auth", "description": "Authentication and token issuance."},
    {"name": "Location", "description": "Endpoints for location-based services."},
]

app = FastAPI(
    title="Score Wind Bike and Run",
    description="Score for running/cycling on specific places.",
    version="1.0.0",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)


protected_api = APIRouter(
    dependencies=[Depends(require_access_token)],
)


@app.get("/", tags=["System"], summary="Service status")
async def root():
    return {"status": "running"}


@app.get(
    "/address-to-lat-long",
    tags=["Location"],
    summary="Get latitude and longitude for an address",
)
async def get_lat_long(address: str) -> dict[str, str]:
    # User openstreetmap's Nominatim API to get latitude and longitude for the given address
    # Give option to select by the response of the answer, but for now just return the first result
    url = "https://nominatim.openstreetmap.org/search"
    response = requests.get(
        url,
        params={"q": address, "format": "json", "limit": 1},
        headers={
            "User-Agent": "wind-score/1.0 (contact: danieloxshimoda@gmail.com)",
            "Referer": "http://localhost:8000/",
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if data:
        lat = data[0]["lat"]
        lon = data[0]["lon"]
        return {"latitude": str(lat), "longitude": str(lon)}
    else:
        return {"error": "Address not found"}


@app.get("/weather/address", tags=["Location"], summary="Get weather for a location")
async def get_weather(address: str):
    lat_long = await get_lat_long(address)
    lat = lat_long.get("latitude")
    lon = lat_long.get("longitude")
    if lat is None or lon is None:
        return {
            "error": "Could not retrieve latitude and longitude for the given address."
        }
    weather = await get_weatherapi_lat_long(lat.strip(), lon.strip())
    generate_grade(weather)
    return weather


app.include_router(security_router, tags=["Auth"])
app.include_router(protected_api)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
