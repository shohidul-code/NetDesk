"""Bills: generation, payment, scoping and the area summary (PROPOSAL §7.2, §8.1, §13.3)."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.services import due_date_for
from app.modules.users.models import User
from tests.factories import make_area, make_bill, make_connection, make_package, make_user

AsUser = Callable[[str], Awaitable[User]]
PAY = {"trx_id": "8N7A6D5E4C", "payment_method": "bkash"}


@pytest.mark.parametrize(
    ("period", "due"),
    [
        ("2026-11", date(2026, 12, 10)),
        ("2026-12", date(2027, 1, 10)),  # December rolls into the next year
        ("2026-01", date(2026, 2, 10)),
    ],
)
def test_due_date_is_the_10th_of_next_month(period: str, due: date) -> None:
    assert due_date_for(period) == due


async def test_generate_twice_creates_then_skips(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await make_connection(db_session)
    await make_connection(db_session, status="suspended")
    await make_connection(db_session, status="disconnected")

    first = await client.post("/api/v1/bills/generate", json={"period": "2026-11"})
    second = await client.post("/api/v1/bills/generate", json={"period": "2026-11"})

    assert first.status_code == 201
    assert first.json() == {"period": "2026-11", "created": 2, "skipped": 0}
    assert second.status_code == 201
    assert second.json() == {"period": "2026-11", "created": 0, "skipped": 2}


async def test_disconnected_connection_gets_no_bill(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    gone = await make_connection(db_session, status="disconnected")

    await client.post("/api/v1/bills/generate", json={"period": "2026-11"})
    listed = await client.get(f"/api/v1/bills?connection_id={gone.id}")

    assert listed.json()["total"] == 0


async def test_bill_amount_is_the_package_price(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    package = await make_package(db_session, monthly_price_bdt=Decimal("1234.50"))
    connection = await make_connection(db_session, package_id=package.id)

    await client.post("/api/v1/bills/generate", json={"period": "2026-12"})
    bill = (await client.get(f"/api/v1/bills?connection_id={connection.id}")).json()["items"][0]

    assert bill["amount_bdt"] == "1234.50"
    assert bill["due_date"] == "2027-01-10"
    assert bill["status"] == "unpaid"


async def test_bad_period_is_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/bills/generate", json={"period": "2026-13"})

    assert response.status_code == 422


async def test_customer_cannot_generate(client: AsyncClient, as_user: AsUser) -> None:
    await as_user("customer")

    response = await client.post("/api/v1/bills/generate", json={"period": "2026-11"})

    assert response.status_code == 403


async def test_customer_sees_only_own_bills(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    other = await make_user(db_session, "customer")
    other_connection = await make_connection(db_session, customer_user_id=other.id)
    await make_bill(db_session, other_connection.id)
    customer = await as_user("customer")
    own_connection = await make_connection(db_session, customer_user_id=customer.id)
    own_bill = await make_bill(db_session, own_connection.id)

    body = (await client.get("/api/v1/bills")).json()

    assert [b["id"] for b in body["items"]] == [str(own_bill.id)]
    assert body["total"] == 1


async def test_list_filters_by_period_and_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    connection = await make_connection(db_session)
    await make_bill(db_session, connection.id, period="2026-10", due_date=date(2026, 11, 10))
    november = await make_bill(db_session, connection.id, period="2026-11")
    base = f"/api/v1/bills?connection_id={connection.id}"

    by_period = (await client.get(f"{base}&period=2026-11")).json()
    paid = (await client.get(f"{base}&status=paid")).json()
    everything = (await client.get(base)).json()

    assert [b["id"] for b in by_period["items"]] == [str(november.id)]
    assert paid["total"] == 0
    assert [b["period"] for b in everything["items"]] == ["2026-11", "2026-10"]  # newest first


async def test_admin_records_payment(
    client: AsyncClient, db_session: AsyncSession, admin: User
) -> None:
    bill = await make_bill(db_session, (await make_connection(db_session)).id)

    response = await client.post(f"/api/v1/bills/{bill.id}/payment", json=PAY)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paid"
    assert body["payment_method"] == "bkash"
    assert body["trx_id"] == "8N7A6D5E4C"
    assert body["paid_at"] is not None
    assert bill.verified_by == admin.id


async def test_trx_id_is_trimmed_and_uppercased(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    bill = await make_bill(db_session, (await make_connection(db_session)).id)

    response = await client.post(
        f"/api/v1/bills/{bill.id}/payment", json={**PAY, "trx_id": "  abc123x "}
    )

    assert response.json()["trx_id"] == "ABC123X"


async def test_same_trx_id_on_another_bill_is_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    connection = await make_connection(db_session)
    bill_a = await make_bill(db_session, connection.id, period="2026-10")
    bill_b = await make_bill(db_session, connection.id, period="2026-11")

    first = await client.post(f"/api/v1/bills/{bill_a.id}/payment", json=PAY)
    second = await client.post(
        f"/api/v1/bills/{bill_b.id}/payment", json={**PAY, "trx_id": "8n7a6d5e4c"}
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["message"] == "This TrxID was already used."


async def test_trx_id_race_is_caught_at_commit(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the pre-check misses (two requests at once), the unique index still answers 409."""
    connection = await make_connection(db_session)
    bill_a = await make_bill(db_session, connection.id, period="2026-10")
    bill_b = await make_bill(db_session, connection.id, period="2026-11")
    await client.post(f"/api/v1/bills/{bill_a.id}/payment", json=PAY)

    async def never_used(*args: object, **kwargs: object) -> bool:
        return False

    monkeypatch.setattr("app.modules.billing.repositories.trx_id_used", never_used)
    response = await client.post(f"/api/v1/bills/{bill_b.id}/payment", json=PAY)

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "This TrxID was already used."


async def test_paying_a_paid_bill_is_409(client: AsyncClient, db_session: AsyncSession) -> None:
    bill = await make_bill(db_session, (await make_connection(db_session)).id)
    await client.post(f"/api/v1/bills/{bill.id}/payment", json=PAY)

    response = await client.post(
        f"/api/v1/bills/{bill.id}/payment", json={**PAY, "trx_id": "ANOTHER99"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "This bill is already paid."


async def test_paying_a_waived_bill_is_409(client: AsyncClient, db_session: AsyncSession) -> None:
    bill = await make_bill(db_session, (await make_connection(db_session)).id, status="waived")

    response = await client.post(f"/api/v1/bills/{bill.id}/payment", json=PAY)

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "This bill was waived."


async def test_payment_on_unknown_bill_is_404(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/bills/{uuid.uuid4()}/payment", json=PAY)

    assert response.status_code == 404


async def test_technician_cannot_record_payment(
    client: AsyncClient, db_session: AsyncSession, as_user: AsUser
) -> None:
    bill = await make_bill(db_session, (await make_connection(db_session)).id)
    await as_user("technician")

    response = await client.post(f"/api/v1/bills/{bill.id}/payment", json=PAY)

    assert response.status_code == 403


async def test_summary_counts_unpaid_bills_per_area(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    mirpur = await make_area(db_session, code="ZZ-MIRPUR")
    uttara = await make_area(db_session, code="ZZ-UTTARA")
    for area, price in [(mirpur, "1000.00"), (mirpur, "500.50"), (uttara, "700.00")]:
        package = await make_package(db_session, monthly_price_bdt=Decimal(price))
        connection = await make_connection(db_session, area_id=area.id, package_id=package.id)
        await make_bill(db_session, connection.id, amount_bdt=Decimal(price))
    paid_connection = await make_connection(db_session, area_id=uttara.id)
    await client.post(
        f"/api/v1/bills/{(await make_bill(db_session, paid_connection.id)).id}/payment", json=PAY
    )

    response = await client.get("/api/v1/bills/summary?period=2026-11")

    mine = [row for row in response.json() if row["area_code"].startswith("ZZ-")]
    assert mine == [
        {
            "area_id": mirpur.id,
            "area_code": "ZZ-MIRPUR",
            "unpaid_count": 2,
            "unpaid_total_bdt": "1500.50",
        },
        {
            "area_id": uttara.id,
            "area_code": "ZZ-UTTARA",
            "unpaid_count": 1,
            "unpaid_total_bdt": "700.00",
        },
    ]


async def test_summary_is_admin_only_and_needs_a_valid_period(
    client: AsyncClient, as_user: AsUser
) -> None:
    assert (await client.get("/api/v1/bills/summary")).status_code == 422
    assert (await client.get("/api/v1/bills/summary?period=2026-13")).status_code == 422
    await as_user("technician")
    assert (await client.get("/api/v1/bills/summary?period=2026-11")).status_code == 403
