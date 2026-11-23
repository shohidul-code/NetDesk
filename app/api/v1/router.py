"""The /api/v1 router. Each feature module's router is included here as it is built."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.db import get_session
from app.core.errors import AppError
from app.modules.areas.controllers import router as areas_router
from app.modules.auth.controllers import router as auth_router
from app.modules.billing.controllers import router as billing_router
from app.modules.chat.controllers import router as chat_router
from app.modules.chat.controllers import usage_router as chat_usage_router
from app.modules.complaints.controllers import router as complaints_router
from app.modules.connections.controllers import router as connections_router
from app.modules.knowledge.controllers import router as knowledge_router
from app.modules.knowledge.retrieval import embeddings_status
from app.modules.notices.controllers import router as notices_router
from app.modules.packages.controllers import router as packages_router
from app.modules.users.controllers import router as users_router

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
    # Embeddings are reported, not required: chat still answers without articles.
    return {
        "status": "ok",
        "version": __version__,
        "db": "ok",
        "embeddings": embeddings_status["status"],
    }


for module_router in (
    auth_router,
    users_router,
    areas_router,
    packages_router,
    connections_router,
    billing_router,
    complaints_router,
    notices_router,
    chat_router,
    chat_usage_router,
    knowledge_router,
):
    api_router.include_router(module_router)
