"""Async database engine and the per-request session.

Routes get a session with `Depends(get_session)`. Services call
`await session.commit()`; repositories only run SQL (CLAUDE.md).
Schema changes go through Alembic only, never `metadata.create_all`.
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """One engine (connection pool) per process, created on first use."""
    return create_async_engine(
        get_settings().database_url.get_secret_value(),
        # Drop dead connections, e.g. after Neon scales to zero.
        pool_pre_ping=True,
        # Give up connecting after 5 s, so /health answers 503 quickly instead of hanging.
        connect_args={"timeout": 5},
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: objects stay readable after the service commits.
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
