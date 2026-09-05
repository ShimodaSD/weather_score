from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

try:
    from .database import pool
    from .routes.router import api_router
except ImportError:
    from database import pool
    from routes.router import api_router


OPENAPI_TAGS = [
    {"name": "System", "description": "Health and service status endpoints."},
    {"name": "Auth", "description": "Authentication and token issuance."},
    {"name": "Location", "description": "Endpoints for location-based services."},
    {"name": "Score", "description": "Weather-based activity scores."},
    {"name": "Grade", "description": "Research-backed activity grading."},
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Manage resources shared for the lifetime of the application."""
    await pool.open()
    try:
        yield
    finally:
        await pool.close()


def create_app() -> FastAPI:
    """Create and configure the API application."""
    application = FastAPI(
        title="Score Wind Bike and Run",
        description="Score for running/cycling on specific places.",
        version="1.0.0",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    application.include_router(api_router)
    return application


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
