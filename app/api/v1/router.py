"""The /api/v1 router. Each feature module's router is included here as it is built."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.db import get_session
from app.core.errors import AppError

api_router = APIRouter(prefix="/api/v1")


class DatabaseUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"


@api_router.get("/health", tags=["health"])
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    """Public check used by Compose, Render and smoke.sh. 503 if the database is down."""
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        raise DatabaseUnavailableError("Database is unavailable.", details={"db": "down"}) from exc
    return {"status": "ok", "version": __version__, "db": "ok"}
