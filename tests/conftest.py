"""Shared test setup.

The required secrets are set here, before `app` is imported, because the app
validates its settings at import time and refuses to start without them.
The values are synthetic test values, not real secrets.

Database tests (PROPOSAL §13.2): the schema is built once with `alembic upgrade head`
(never create_all). Each test runs inside a transaction that is rolled back, and the
app's own commits become SAVEPOINTs inside it, so tests never see each other's rows.
"""

import os
import subprocess
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

# Host port 5433, so it does not clash with a local PostgreSQL on 5432.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://netdesk:netdesk@localhost:5433/netdesk")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-used-anywhere-else-0123")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.auth.dependencies import get_current_user  # noqa: E402
from app.modules.users.models import User  # noqa: E402
from tests.factories import make_user  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    subprocess.run(["alembic", "upgrade", "head"], cwd=REPO_ROOT, check=True, capture_output=True)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest.fixture
async def admin(db_session: AsyncSession) -> User:
    return await make_user(db_session, "admin")


@pytest.fixture
def app(db_session: AsyncSession, admin: User) -> FastAPI:
    """The app wired to the test transaction. Requests act as `admin` by default."""
    application = create_app()

    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_session] = test_session
    application.dependency_overrides[get_current_user] = lambda: admin
    return application


@pytest.fixture
def as_user(app: FastAPI, db_session: AsyncSession) -> Callable[[str], Awaitable[User]]:
    """Switch the current user: `customer = await as_user("customer")`."""

    async def switch(role: str) -> User:
        user = await make_user(db_session, role)
        app.dependency_overrides[get_current_user] = lambda: user
        return user

    return switch


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """An HTTP client that calls the app in memory, without a real server."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
