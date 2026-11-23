"""Complaints: scoped reads, role-gated writes, a small status state machine."""

from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.users.models import User
from tests.factories import make_area, make_complaint, make_connection, make_user

AsUser = Callable[[str], Awaitable[User]]


def _body(connection_id: object, **overrides: object) -> dict[str, object]:
    return {
        "connection_id": str(connection_id),
        "category": "no_internet",
        "description": "Internet is down.",
        **overrides,
    }


async def test_customer_creates_complaint_on_own_connection(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    connection = await make_connection(db_session, customer_user_id=customer.id)

    response = await client.post("/api/v1/complaints", json=_body(connection.id))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["created_by"] == str(customer.id)
    assert body["assigned_to"] is None


async def test_customer_cannot_complain_on_someone_elses_connection(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    other = await make_connection(db_session)
    await as_user("customer")

    response = await client.post("/api/v1/complaints", json=_body(other.id))

    assert response.status_code == 404


async def test_technician_cannot_create_complaint(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    connection = await make_connection(db_session)
    await as_user("technician")

    response = await client.post("/api/v1/complaints", json=_body(connection.id))

    assert response.status_code == 403


async def test_admin_creates_complaint_on_any_connection(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    connection = await make_connection(db_session)

    response = await client.post("/api/v1/complaints", json=_body(connection.id))
    missing = await client.post(
        "/api/v1/complaints", json=_body("00000000-0000-0000-0000-000000000000")
    )

    assert response.status_code == 201
    assert missing.status_code == 404


async def test_flag_off_blocks_customer_but_not_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    as_user: AsUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "allow_customer_complaints", False)
    customer = await as_user("customer")
    connection = await make_connection(db_session, customer_user_id=customer.id)

    as_customer = await client.post("/api/v1/complaints", json=_body(connection.id))
    await as_user("admin")
    as_admin = await client.post("/api/v1/complaints", json=_body(connection.id))

    assert as_customer.status_code == 403
    assert as_admin.status_code == 201


async def test_description_over_1000_chars_is_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    connection = await make_connection(db_session)

    response = await client.post(
        "/api/v1/complaints", json=_body(connection.id, description="x" * 1001)
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "description"


async def test_customer_list_shows_only_own_complaints(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    mine = await make_connection(db_session, customer_user_id=customer.id)
    theirs = await make_connection(db_session)
    own = await make_complaint(db_session, mine.id, customer.id)
    await make_complaint(db_session, theirs.id, customer.id)

    body = (await client.get("/api/v1/complaints")).json()

    assert [c["id"] for c in body["items"]] == [str(own.id)]
    assert body["total"] == 1


async def test_staff_list_filters_by_area_and_status(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    area = await make_area(db_session)
    here = await make_connection(db_session, area_id=area.id)
    elsewhere = await make_connection(db_session)
    target = await make_complaint(db_session, here.id, admin.id, status="in_progress")
    await make_complaint(db_session, here.id, admin.id)
    await make_complaint(db_session, elsewhere.id, admin.id, status="in_progress")

    async def ids(query: str) -> list[str]:
        response = await client.get(f"/api/v1/complaints?{query}")
        return [c["id"] for c in response.json()["items"]]

    assert await ids(f"area_id={area.id}&status=in_progress") == [str(target.id)]
    assert len(await ids(f"area_id={area.id}")) == 2


async def test_status_chain_is_allowed(
    client: AsyncClient, db_session: AsyncSession, admin: User, as_user: AsUser
) -> None:
    complaint = await make_complaint(db_session, (await make_connection(db_session)).id, admin.id)
    await as_user("technician")

    for status in ("in_progress", "resolved", "in_progress", "resolved", "closed"):
        response = await client.patch(f"/api/v1/complaints/{complaint.id}", json={"status": status})
        assert response.status_code == 200
        assert response.json()["status"] == status


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("open", "closed"),
        ("open", "resolved"),
        ("open", "open"),
        ("in_progress", "open"),
        ("in_progress", "closed"),
        ("closed", "open"),
        ("closed", "in_progress"),
    ],
)
async def test_invalid_transition_is_409(
    client: AsyncClient, db_session: AsyncSession, admin: User, current: str, target: str
) -> None:
    connection = await make_connection(db_session)
    complaint = await make_complaint(db_session, connection.id, admin.id, status=current)

    response = await client.patch(f"/api/v1/complaints/{complaint.id}", json={"status": target})

    assert response.status_code == 409
    assert (
        response.json()["error"]["message"] == f"Cannot change status from {current} to {target}."
    )


async def test_technician_cannot_assign(
    client: AsyncClient, db_session: AsyncSession, admin: User, as_user: AsUser
) -> None:
    complaint = await make_complaint(db_session, (await make_connection(db_session)).id, admin.id)
    technician = await as_user("technician")

    response = await client.patch(
        f"/api/v1/complaints/{complaint.id}", json={"assigned_to": str(technician.id)}
    )

    assert response.status_code == 403


async def test_admin_assigns_and_unassigns_technician(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    technician = await make_user(db_session, "technician")
    complaint = await make_complaint(db_session, (await make_connection(db_session)).id, admin.id)

    assigned = await client.patch(
        f"/api/v1/complaints/{complaint.id}", json={"assigned_to": str(technician.id)}
    )
    cleared = await client.patch(f"/api/v1/complaints/{complaint.id}", json={"assigned_to": None})

    assert assigned.status_code == 200
    assert assigned.json()["assigned_to"] == str(technician.id)
    assert cleared.json()["assigned_to"] is None


async def test_assigning_a_non_technician_is_404(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    customer = await make_user(db_session, "customer")
    inactive = await make_user(db_session, "technician", is_active=False)
    complaint = await make_complaint(db_session, (await make_connection(db_session)).id, admin.id)

    for user in (customer, inactive):
        response = await client.patch(
            f"/api/v1/complaints/{complaint.id}", json={"assigned_to": str(user.id)}
        )
        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Technician not found."


async def test_customer_cannot_update_complaint(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    connection = await make_connection(db_session, customer_user_id=customer.id)
    complaint = await make_complaint(db_session, connection.id, customer.id)

    response = await client.patch(
        f"/api/v1/complaints/{complaint.id}", json={"status": "in_progress"}
    )

    assert response.status_code == 403


async def test_update_missing_complaint_is_404(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/complaints/00000000-0000-0000-0000-000000000000", json={"status": "in_progress"}
    )

    assert response.status_code == 404
