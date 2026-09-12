"""GarminDB activity synchronization routes."""

from fastapi import APIRouter

try:
    from ..services.garmin import sync_activities
except ImportError:
    from services.garmin import sync_activities

router = APIRouter(prefix="/garmin", tags=["Garmin"])


@router.post("/sync", summary="Upload all GarminDB activities to PostgreSQL")
async def sync_garmin_activities() -> dict[str, int]:
    """Synchronize the configured GarminDB activities database."""
    return {"synced": await sync_activities()}
