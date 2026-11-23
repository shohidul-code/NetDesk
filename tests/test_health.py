"""Health check. Needs the database from `docker compose up -d db` (host port 5433)."""

from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import __version__
from app.core.db import get_session
from app.main import create_app

# Nothing listens on port 1, so connecting fails at once: a deterministic "DB is down".
UNREACHABLE_DB = "postgresql+asyncpg://netdesk:netdesk@127.0.0.1:1/netdesk"


async def test_health_returns_200_with_db_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": __version__,
        "db": "ok",
        "embeddings": "ok",
    }


async def test_health_returns_503_when_db_is_down() -> None:
    engine = create_async_engine(UNREACHABLE_DB)

    async def broken_session() -> AsyncIterator[AsyncSession]:
        async with async_sessionmaker(engine)() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = broken_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/v1/health")
    finally:
        await engine.dispose()

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "service_unavailable"
    assert error["details"] == {"db": "down"}


async def test_docs_are_public(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
