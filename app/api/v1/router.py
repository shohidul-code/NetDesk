"""The /api/v1 router. Each feature module's router is included here as it is built."""

from fastapi import APIRouter

from app import __version__

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Public liveness check. The database status is added in Phase 1, task 3."""
    return {"status": "ok", "version": __version__}
