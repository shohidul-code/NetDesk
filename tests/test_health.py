from httpx import AsyncClient

from app import __version__


async def test_health_returns_200_with_version(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


async def test_docs_are_public(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
