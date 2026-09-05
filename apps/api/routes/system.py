"""System status endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/", summary="Service status")
async def service_status() -> dict[str, str]:
    """Return the current service status."""
    return {"status": "running"}
