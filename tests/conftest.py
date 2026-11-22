"""Shared test setup.

The required secrets are set here, before `app` is imported, because the app
validates its settings at import time and refuses to start without them.
The values are synthetic test values, not real secrets.
"""

import os
from collections.abc import AsyncIterator

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://netdesk:netdesk@localhost:5432/netdesk")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-used-anywhere-else-0123")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """An HTTP client that calls the app in memory, without a real server."""
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
