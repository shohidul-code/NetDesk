"""Area notices: admin writes, customers see only their own areas (PROPOSAL §8.1)."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from tests.factories import make_area, make_connection, make_notice

AsUser = Callable[[str], Awaitable[User]]
NOW = datetime.now(UTC)


def new_notice(area_id: int, **overrides: object) -> dict[str, object]:
    body = {
        "area_id": area_id,
        "kind": "maintenance",
        "message_bn": "রাত ২টা থেকে ৪টা পর্যন্ত রক্ষণাবেক্ষণ।",
        "message_en": "Maintenance from 2 to 4 am.",
        "starts_at": (NOW + timedelta(hours=1)).isoformat(),
        "ends_at": (NOW + timedelta(hours=3)).isoformat(),
    }
    return {**body, **overrides}


async def test_admin_creates_notice_and_bangla_round_trips(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    area = await make_area(db_session)
    body = new_notice(area.id)

    created = await client.post("/api/v1/notices", json=body)
    listed = await client.get(f"/api/v1/notices?area_id={area.id}")

    assert created.status_code == 201
    assert created.json()["message_bn"] == body["message_bn"]
    assert created.json()["created_by"] == str(admin.id)
    assert created.json() in listed.json()


async def test_ends_before_starts_is_422(client: AsyncClient, db_session: AsyncSession) -> None:
    area = await make_area(db_session)
    body = new_notice(area.id, ends_at=(NOW - timedelta(hours=1)).isoformat())

    response = await client.post("/api/v1/notices", json=body)

    assert response.status_code == 422


async def test_naive_datetime_is_422(client: AsyncClient, db_session: AsyncSession) -> None:
    area = await make_area(db_session)
    body = new_notice(area.id, starts_at="2026-12-01T10:00:00")

    response = await client.post("/api/v1/notices", json=body)

    assert response.status_code == 422


async def test_notice_for_unknown_area_is_404(client: AsyncClient) -> None:
    response = await client.post("/api/v1/notices", json=new_notice(999999))

    assert response.status_code == 404


async def test_customer_cannot_create_notice(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    area = await make_area(db_session)
    await as_user("customer")

    response = await client.post("/api/v1/notices", json=new_notice(area.id))

    assert response.status_code == 403


async def test_customer_sees_only_notices_for_own_areas(
    client: AsyncClient, db_session: AsyncSession, admin: User, as_user: AsUser
) -> None:
    own_area = await make_area(db_session)
    other_area = await make_area(db_session)
    own = await make_notice(db_session, own_area.id, admin.id)
    await make_notice(db_session, other_area.id, admin.id)
    customer = await as_user("customer")
    await make_connection(db_session, area_id=own_area.id, customer_user_id=customer.id)

    response = await client.get("/api/v1/notices")

    assert [n["id"] for n in response.json()] == [str(own.id)]


async def test_active_filter(client: AsyncClient, db_session: AsyncSession, admin: User) -> None:
    area = await make_area(db_session)
    current = await make_notice(db_session, area.id, admin.id)
    expired = await make_notice(
        db_session,
        area.id,
        admin.id,
        starts_at=NOW - timedelta(days=2),
        ends_at=NOW - timedelta(days=1),
    )
    future = await make_notice(
        db_session,
        area.id,
        admin.id,
        starts_at=NOW + timedelta(days=1),
        ends_at=NOW + timedelta(days=2),
    )
    base = f"/api/v1/notices?area_id={area.id}"

    active = {n["id"] for n in (await client.get(f"{base}&active=true")).json()}
    inactive = {n["id"] for n in (await client.get(f"{base}&active=false")).json()}
    everything = {n["id"] for n in (await client.get(base)).json()}

    assert active == {str(current.id)}
    assert inactive == {str(expired.id), str(future.id)}
    assert everything == active | inactive


async def test_admin_updates_notice(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    area = await make_area(db_session)
    notice = await make_notice(db_session, area.id, admin.id)

    response = await client.patch(
        f"/api/v1/notices/{notice.id}", json={"message_en": "Fixed.", "kind": "maintenance"}
    )

    assert response.status_code == 200
    assert response.json()["message_en"] == "Fixed."
    assert response.json()["message_bn"] == notice.message_bn


async def test_patch_that_ends_before_start_is_422(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    area = await make_area(db_session)
    notice = await make_notice(db_session, area.id, admin.id)
    earlier = (notice.starts_at - timedelta(hours=1)).isoformat()

    response = await client.patch(f"/api/v1/notices/{notice.id}", json={"ends_at": earlier})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_patch_unknown_notice_is_404(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/notices/00000000-0000-0000-0000-000000000000", json={"message_en": "x"}
    )

    assert response.status_code == 404


async def test_patch_to_unknown_area_is_404(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    notice = await make_notice(db_session, (await make_area(db_session)).id, admin.id)

    response = await client.patch(f"/api/v1/notices/{notice.id}", json={"area_id": 999999})

    assert response.status_code == 404
