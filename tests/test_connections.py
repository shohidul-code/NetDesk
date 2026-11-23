"""Connections (PROPOSAL §8.1, §8.2, §13.3): scoped reads, admin-only writes."""

from collections.abc import Awaitable, Callable
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from tests.factories import make_area, make_bill, make_complaint, make_connection, make_package

AsUser = Callable[[str], Awaitable[User]]


async def _new_body(db_session: AsyncSession, **overrides: Any) -> dict[str, Any]:
    area = await make_area(db_session)
    package = await make_package(db_session)
    return {
        "customer_code": "ND-900001",
        "customer_name": "Test Customer",
        "phone": "01712345678",
        "address": "House 1, Test Road",
        "area_id": area.id,
        "package_id": package.id,
        **overrides,
    }


async def test_admin_creates_connection_and_it_is_listed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    created = await client.post("/api/v1/connections", json=await _new_body(db_session))
    listed = await client.get("/api/v1/connections")

    assert created.status_code == 201
    assert created.json()["phone"] == "+8801712345678"
    assert created.json()["status"] == "active"
    assert created.json() in listed.json()["items"]


async def test_duplicate_customer_code_is_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    body = await _new_body(db_session)
    await client.post("/api/v1/connections", json=body)

    response = await client.post("/api/v1/connections", json=body)

    assert response.status_code == 409


async def test_customer_cannot_create_connection(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    body = await _new_body(db_session)
    await as_user("customer")

    response = await client.post("/api/v1/connections", json=body)

    assert response.status_code == 403


async def test_bad_phone_is_422_on_phone_field(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    body = await _new_body(db_session, phone="12345")

    response = await client.post("/api/v1/connections", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "phone"


async def test_bad_customer_code_is_422(client: AsyncClient, db_session: AsyncSession) -> None:
    body = await _new_body(db_session, customer_code="ND-12")

    response = await client.post("/api/v1/connections", json=body)

    assert response.status_code == 422


async def test_unknown_area_or_package_is_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    bad_area = await client.post(
        "/api/v1/connections", json=await _new_body(db_session, area_id=999999)
    )
    bad_package = await client.post(
        "/api/v1/connections", json=await _new_body(db_session, package_id=999999)
    )

    assert bad_area.status_code == 404
    assert bad_area.json()["error"]["message"] == "Area not found."
    assert bad_package.status_code == 404
    assert bad_package.json()["error"]["message"] == "Package not found."


async def test_customer_sees_only_own_connection(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    mine = await make_connection(db_session, customer_user_id=customer.id)
    await make_connection(db_session)

    body = (await client.get("/api/v1/connections")).json()

    assert [c["id"] for c in body["items"]] == [str(mine.id)]
    assert body["total"] == 1


async def test_other_customers_connection_is_404(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    other = await make_connection(db_session)
    await as_user("customer")

    response = await client.get(f"/api/v1/connections/{other.id}")

    assert response.status_code == 404


async def test_customer_reads_own_connection(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    mine = await make_connection(db_session, customer_user_id=customer.id)

    response = await client.get(f"/api/v1/connections/{mine.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(mine.id)


async def test_missing_connection_is_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/connections/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


async def test_filters_by_area_status_and_package(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    target = await make_connection(db_session, status="suspended")
    await make_connection(db_session)

    async def ids(query: str) -> list[str]:
        response = await client.get(f"/api/v1/connections?{query}")
        return [c["id"] for c in response.json()["items"]]

    assert await ids(f"area_id={target.area_id}") == [str(target.id)]
    assert await ids(f"package_id={target.package_id}") == [str(target.id)]
    assert str(target.id) in await ids("status=suspended")
    assert await ids(f"area_id={target.area_id}&status=active") == []


async def test_q_matches_code_name_or_phone(client: AsyncClient, db_session: AsyncSession) -> None:
    target = await make_connection(
        db_session, customer_code="ND-777001", customer_name="Rahim Uddin", phone="+8801811111111"
    )

    async def ids(q: str) -> list[str]:
        response = await client.get("/api/v1/connections", params={"q": q})
        return [c["id"] for c in response.json()["items"]]

    assert await ids("777001") == [str(target.id)]
    assert await ids("rahim UDDIN") == [str(target.id)]
    assert await ids("01811111") == [str(target.id)]


async def test_q_escapes_like_wildcards_and_sql(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await make_connection(db_session)

    injection = await client.get("/api/v1/connections", params={"q": "%' OR 1=1 --"})
    wildcard = await client.get("/api/v1/connections", params={"q": "%"})

    assert injection.status_code == 200
    assert injection.json()["total"] == 0
    assert wildcard.json()["total"] == 0  # a literal % is not "match everything"


async def test_sort_descending_and_default(client: AsyncClient, db_session: AsyncSession) -> None:
    await make_connection(db_session, customer_code="ND-100001")
    await make_connection(db_session, customer_code="ND-100002")

    async def codes(query: str) -> list[str]:
        response = await client.get(f"/api/v1/connections?q=ND-10000&{query}")
        return [c["customer_code"] for c in response.json()["items"]]

    assert await codes("sort=-customer_code") == ["ND-100002", "ND-100001"]
    assert await codes("") == ["ND-100001", "ND-100002"]


async def test_unknown_sort_is_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/connections?sort=password")

    assert response.status_code == 422


async def test_limit_over_100_is_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/connections?limit=101")

    assert response.status_code == 422


async def test_pagination_reports_total_limit_offset(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    for code in ("ND-200001", "ND-200002", "ND-200003"):
        await make_connection(db_session, customer_code=code)

    body = (await client.get("/api/v1/connections?q=ND-2000&limit=2&offset=2")).json()

    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 2
    assert [c["customer_code"] for c in body["items"]] == ["ND-200003"]


async def test_update_connection(client: AsyncClient, db_session: AsyncSession) -> None:
    connection = await make_connection(db_session)
    package = await make_package(db_session)

    response = await client.patch(
        f"/api/v1/connections/{connection.id}",
        json={"status": "suspended", "package_id": package.id},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "suspended"
    assert response.json()["package_id"] == package.id


async def test_update_with_unknown_package_is_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    connection = await make_connection(db_session)

    response = await client.patch(
        f"/api/v1/connections/{connection.id}", json={"package_id": 999999}
    )

    assert response.status_code == 404


async def test_customer_code_cannot_be_changed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    connection = await make_connection(db_session)

    response = await client.patch(
        f"/api/v1/connections/{connection.id}", json={"customer_code": "ND-999999"}
    )

    assert response.status_code == 422


async def test_customer_cannot_update_connection(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    customer = await as_user("customer")
    mine = await make_connection(db_session, customer_user_id=customer.id)

    response = await client.patch(f"/api/v1/connections/{mine.id}", json={"status": "active"})

    assert response.status_code == 403


async def test_delete_connection_with_bills_is_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    connection = await make_connection(db_session)
    await make_bill(db_session, connection.id)

    response = await client.delete(f"/api/v1/connections/{connection.id}")

    assert response.status_code == 409


async def test_delete_connection_without_bills_is_204(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    connection = await make_connection(db_session)

    deleted = await client.delete(f"/api/v1/connections/{connection.id}")
    again = await client.get(f"/api/v1/connections/{connection.id}")

    assert deleted.status_code == 204
    assert again.status_code == 404


async def test_delete_missing_connection_is_404(client: AsyncClient) -> None:
    response = await client.delete("/api/v1/connections/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


async def test_delete_connection_with_complaints_is_409(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    """Without this check the RESTRICT foreign key would turn the delete into a 500."""
    connection = await make_connection(db_session)
    await make_complaint(db_session, connection.id, admin.id)

    response = await client.delete(f"/api/v1/connections/{connection.id}")

    assert response.status_code == 409
