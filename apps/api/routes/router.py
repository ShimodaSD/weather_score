"""Top-level API router composition."""

from fastapi import APIRouter

try:
    from ..security import require_access_token
    from ..security import router as security_router
except ImportError:
    from security import router as security_router

from .location import router as location_router
from .run_grade import router as run_grade_router
from .score import router as score_router
from .system import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(security_router)
api_router.include_router(location_router)
api_router.include_router(score_router)
api_router.include_router(
    run_grade_router,
    # dependencies=[Depends(require_access_token)],
)
