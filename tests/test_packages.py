"""Areas and packages (PROPOSAL §8.1). Admin writes; everyone reads."""

from collections.abc import Awaitable, Callable

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from tests.factories import make_area, make_connection, make_package

AsUser = Callable[[str], Awaitable[User]]
NEW_PACKAGE = {"name": "Fibre 40", "speed_mbps": 40, "monthly_price_bdt": "1500.00"}


async def test_areas_are_listed(client: AsyncClient, db_session: AsyncSession) -> None:
    area = await make_area(db_session, code="MIRPUR-10")

    response = await client.get("/api/v1/areas")

    assert response.status_code == 200
    assert {"id": area.id, "code": "MIRPUR-10", "name": area.name, "name_bn": area.name_bn} in (
        response.json()
    )


async def test_admin_creates_package_and_it_is_listed(client: AsyncClient) -> None:
    created = await client.post("/api/v1/packages", json=NEW_PACKAGE)
    listed = await client.get("/api/v1/packages")

    assert created.status_code == 201
    assert created.json()["monthly_price_bdt"] == "1500.00"
    assert created.json() in listed.json()


async def test_duplicate_package_name_is_409(client: AsyncClient) -> None:
    await client.post("/api/v1/packages", json=NEW_PACKAGE)

    response = await client.post("/api/v1/packages", json=NEW_PACKAGE)

    assert response.status_code == 409


async def test_customer_cannot_create_package(client: AsyncClient, as_user: AsUser) -> None:
    await as_user("customer")

    response = await client.post("/api/v1/packages", json=NEW_PACKAGE)

    assert response.status_code == 403


async def test_zero_speed_is_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/packages", json={**NEW_PACKAGE, "speed_mbps": 0})

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "speed_mbps"


async def test_customer_sees_only_active_packages(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    active = await make_package(db_session)
    retired = await make_package(db_session, is_active=False)
    await as_user("customer")

    ids = {p["id"] for p in (await client.get("/api/v1/packages")).json()}

    assert active.id in ids
    assert retired.id not in ids


async def test_staff_can_filter_inactive(client: AsyncClient, db_session: AsyncSession) -> None:
    retired = await make_package(db_session, is_active=False)

    ids = {p["id"] for p in (await client.get("/api/v1/packages?active=false")).json()}

    assert retired.id in ids


async def test_update_package(client: AsyncClient, db_session: AsyncSession) -> None:
    package = await make_package(db_session)

    response = await client.patch(
        f"/api/v1/packages/{package.id}", json={"monthly_price_bdt": "1200.50"}
    )

    assert response.status_code == 200
    assert response.json()["monthly_price_bdt"] == "1200.50"


async def test_update_unknown_package_is_404(client: AsyncClient) -> None:
    response = await client.patch("/api/v1/packages/999999", json={"speed_mbps": 10})

    assert response.status_code == 404


async def test_unknown_field_is_rejected(client: AsyncClient, db_session: AsyncSession) -> None:
    """extra="forbid" blocks mass assignment of fields the schema does not list."""
    package = await make_package(db_session)

    response = await client.patch(f"/api/v1/packages/{package.id}", json={"id": 5})

    assert response.status_code == 422


async def test_delete_unused_package_is_204(client: AsyncClient, db_session: AsyncSession) -> None:
    package = await make_package(db_session)

    response = await client.delete(f"/api/v1/packages/{package.id}")

    assert response.status_code == 204


async def test_delete_package_in_use_is_409(client: AsyncClient, db_session: AsyncSession) -> None:
    connection = await make_connection(db_session)

    response = await client.delete(f"/api/v1/packages/{connection.package_id}")

    assert response.status_code == 409
