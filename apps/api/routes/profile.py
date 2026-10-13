"""Authenticated athlete profile endpoints."""

from fastapi import APIRouter, Depends

try:
    from ..schemas.profile import ProfileResponse, ProfileUpdate
    from ..security import require_access_token
    from ..services.profile import fetch_profile, save_profile
except ImportError:
    from schemas.profile import ProfileResponse, ProfileUpdate
    from security import require_access_token
    from services.profile import fetch_profile, save_profile


router = APIRouter(
    prefix="/profile", tags=["Profile"], dependencies=[Depends(require_access_token)]
)


@router.get("", response_model=ProfileResponse)
async def get_profile() -> dict[str, object]:
    """Return the saved profile or its initial 157 bpm threshold."""
    return await fetch_profile()


@router.put("", response_model=ProfileResponse)
async def update_profile(profile: ProfileUpdate) -> dict[str, object]:
    """Save the name and threshold used for automatic activity TSS."""
    return await save_profile(profile.name, profile.threshold_heart_rate_bpm)
