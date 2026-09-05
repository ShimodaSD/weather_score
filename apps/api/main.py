import asyncio
from contextlib import asynccontextmanager
from typing import Literal

import requests
import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status

from weather_score.application.main import generate_grade, generate_grade_by_type
from weather_score.weather.providers.openmeteo import get_openmeteo_altitude
from weather_score.weather.providers.weather_api import get_weatherapi_lat_long

try:
    from .database import pool
    from .routes.run_grade import router as run_grade_router
    from .security import require_access_token, security_router
except ImportError:
    from database import pool
    from routes.run_grade import router as run_grade_router
    from security import require_access_token, security_router


TrainingRunType = Literal["easy", "long", "threshold", "interval", "speed"]


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
    {"name": "Grade", "description": "Research-backed activity grading."},
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
    url = "https://nominatim.openstreetmap.org/search"
    try:
        response = await asyncio.to_thread(
            requests.get,
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
    except (requests.RequestException, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve coordinates.",
        ) from error

    if data:
        lat = data[0]["lat"]
        lon = data[0]["lon"]
        return {"latitude": str(lat), "longitude": str(lon)}
    return {"error": "Address not found"}


async def _score_address(
    address: str,
    training_type: TrainingRunType | None = None,
) -> float | dict[str, str]:
    lat_long = await get_lat_long(address)
    lat = lat_long.get("latitude")
    lon = lat_long.get("longitude")
    if lat is None or lon is None:
        return {
            "error": "Could not retrieve latitude and longitude for the given address."
        }
    try:
        weather, altitude = await asyncio.gather(
            get_weatherapi_lat_long(lat.strip(), lon.strip()),
            get_openmeteo_altitude(lat.strip(), lon.strip()),
        )
        if training_type is not None:
            return await generate_grade_by_type(weather, altitude, training_type)
        return await generate_grade(weather, altitude)
    except (requests.RequestException, TimeoutError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve weather data.",
        ) from error


@app.get("/score/run", tags=["Location"], summary="Score running conditions")
async def score_run(address: str) -> float | dict[str, str]:
    return await _score_address(address)


@app.get(
    "/score/run/by-type",
    tags=["Location"],
    summary="Score conditions for a running workout type",
)
async def score_run_by_type(
    address: str,
    training_type: TrainingRunType,
) -> float | dict[str, str]:
    return await _score_address(address, training_type)


app.include_router(security_router, tags=["Auth"])
app.include_router(
    run_grade_router,
    dependencies=[Depends(require_access_token)],
)
app.include_router(protected_api)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
