"""/users: admin-only staff management (PROPOSAL §8.1)."""

import uuid
from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import Role, User
from tests.factories import make_user

URL = "/api/v1/users"
PASSWORD = "a-long-enough-password"


def _new(**kw: object) -> dict[str, object]:
    return {
        "email": "Tech.One@Example.test",
        "full_name": "Test Technician",
        "password": PASSWORD,
        **kw,
    }


async def test_admin_creates_a_technician(client: AsyncClient) -> None:
    response = await client.post(URL, json=_new())

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "technician"
    assert body["email"] == "tech.one@example.test"
    assert body["is_active"] is True
    assert "password" not in response.text


async def test_role_in_the_body_is_rejected(client: AsyncClient) -> None:
    response = await client.post(URL, json=_new(role="admin"))

    assert response.status_code == 422


async def test_duplicate_email_is_409(client: AsyncClient, db_session: AsyncSession) -> None:
    existing = await make_user(db_session, "customer")

    response = await client.post(URL, json=_new(email=existing.email))

    assert response.status_code == 409


@pytest.mark.parametrize("change", [{"password": "short"}, {"full_name": "x"}, {"email": "nope"}])
async def test_create_validates_input(client: AsyncClient, change: dict[str, object]) -> None:
    response = await client.post(URL, json=_new(**change))

    assert response.status_code == 422


async def test_list_filters_by_role_and_pages(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    for _ in range(3):
        await make_user(db_session, "technician")

    response = await client.get(URL, params={"role": "technician", "limit": 2})

    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 2
    assert body["total"] >= 3
    assert body["limit"] == 2 and body["offset"] == 0
    assert {u["role"] for u in body["items"]} == {"technician"}


async def test_list_without_filter_includes_every_role(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await make_user(db_session, "customer")

    response = await client.get(URL, params={"limit": 100})

    assert {"admin", "customer"} <= {u["role"] for u in response.json()["items"]}


async def test_list_rejects_an_unknown_role(client: AsyncClient) -> None:
    response = await client.get(URL, params={"role": "root"})

    assert response.status_code == 422


async def test_admin_updates_name_and_active_flag(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    tech = await make_user(db_session, "technician")

    response = await client.patch(
        f"{URL}/{tech.id}", json={"full_name": "Renamed Tech", "is_active": False}
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Renamed Tech"
    assert response.json()["is_active"] is False


async def test_update_cannot_change_role_or_email(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    tech = await make_user(db_session, "technician")

    response = await client.patch(f"{URL}/{tech.id}", json={"role": "admin"})

    assert response.status_code == 422


async def test_update_missing_user_is_404(client: AsyncClient) -> None:
    response = await client.patch(f"{URL}/{uuid.uuid4()}", json={"is_active": False})

    assert response.status_code == 404


async def test_cannot_deactivate_the_last_active_admin(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    # The shared dev database may hold seeded admins; this test needs exactly one.
    admin_role_id = select(Role.id).where(Role.name == "admin").scalar_subquery()
    await db_session.execute(
        update(User)
        .where(User.role_id == admin_role_id, User.id != admin.id)
        .values(is_active=False)
    )

    response = await client.patch(f"{URL}/{admin.id}", json={"is_active": False})

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Cannot deactivate the last active admin."


async def test_can_deactivate_an_admin_when_another_is_active(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    other = await make_user(db_session, "admin")

    response = await client.patch(f"{URL}/{other.id}", json={"is_active": False})

    assert response.status_code == 200


@pytest.mark.parametrize("role", ["customer", "technician"])
async def test_non_admins_get_403_on_every_users_route(
    client: AsyncClient, as_user: Callable[[str], Awaitable[User]], role: str
) -> None:
    await as_user(role)
    some_id = uuid.uuid4()

    responses = [
        await client.get(URL),
        await client.post(URL, json=_new()),
        await client.patch(f"{URL}/{some_id}", json={"is_active": False}),
    ]

    assert [r.status_code for r in responses] == [403, 403, 403]
