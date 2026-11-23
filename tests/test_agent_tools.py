"""Agent tool registry (PROPOSAL §9.5): per-role tool sets, server-side authorization,
argument validation, timeout and size cap. Calls `execute` directly, no HTTP."""

import asyncio
import inspect
import json
import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent import registry, tools
from app.modules.agent.registry import REGISTRY, execute, tools_for
from app.modules.users.models import User
from tests.factories import (
    make_area,
    make_bill,
    make_complaint,
    make_connection,
    make_notice,
    make_user,
)

CUSTOMER_TOOLS = {"get_my_bill_status", "get_my_area_status"}
STAFF_TOOLS = {"lookup_customer_bills", "get_area_service_status"}
# Valid arguments for every tool, so a refusal can only come from the role check.
VALID_ARGS = {
    "get_my_bill_status": "{}",
    "get_my_area_status": "{}",
    "lookup_customer_bills": '{"customer_code": "ND-000001"}',
    "get_area_service_status": '{"area_code": "NOPE"}',
}
ROLE_TOOLS = {"customer": CUSTOMER_TOOLS, "technician": STAFF_TOOLS, "admin": STAFF_TOOLS}


async def run(session: AsyncSession, user: User, name: str, args: str = "{}") -> dict[str, Any]:
    outcome = await execute(session, user, name, args)
    return {"ok": outcome.ok, **json.loads(outcome.content)}


async def customer_with_bills(db: AsyncSession) -> tuple[User, Any]:
    customer = await make_user(db, "customer")
    connection = await make_connection(db, customer_user_id=customer.id)
    return customer, connection


@pytest.mark.parametrize("role", ["customer", "technician", "admin"])
@pytest.mark.parametrize("tool", sorted(CUSTOMER_TOOLS | STAFF_TOOLS))
async def test_tool_is_refused_exactly_when_role_not_allowed(
    db_session: AsyncSession, caplog: pytest.LogCaptureFixture, role: str, tool: str
) -> None:
    user = await make_user(db_session, role)
    with caplog.at_level(logging.WARNING):
        outcome = await execute(db_session, user, tool, VALID_ARGS[tool])

    refused = outcome.content == '{"error": "tool_not_available"}'
    logged = [r.getMessage() for r in caplog.records if "tool_not_available" in r.getMessage()]
    assert refused == (tool not in ROLE_TOOLS[role])
    assert outcome.name == tool
    if refused:
        assert outcome.ok is False
        assert len(logged) == 1 and tool in logged[0] and str(user.id) in logged[0]
    else:
        assert not logged


async def test_unknown_tool_is_refused_and_logged(
    db_session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    admin = await make_user(db_session, "admin")
    with caplog.at_level(logging.WARNING):
        result = await run(db_session, admin, "delete_everything")

    assert result == {"ok": False, "error": "tool_not_available"}
    assert "delete_everything" in caplog.text


def test_tools_for_lists_only_the_roles_tools() -> None:
    names = {role: {t["function"]["name"] for t in tools_for(role)} for role in ROLE_TOOLS}  # type: ignore[arg-type]
    assert names["customer"] == CUSTOMER_TOOLS
    assert names["technician"] == names["admin"] == STAFF_TOOLS
    for spec in tools_for("admin"):
        assert spec["type"] == "function"
        assert spec["function"]["description"]
        assert spec["function"]["parameters"]["type"] == "object"


def test_each_handler_is_at_most_20_lines() -> None:
    handlers = [definition.handler for definition in REGISTRY.values()]
    assert {h.__name__ for h in handlers} == CUSTOMER_TOOLS | STAFF_TOOLS
    for handler in handlers:
        assert handler is getattr(tools, handler.__name__)
        assert len(inspect.getsourcelines(handler)[0]) <= 20


# --- get_my_bill_status ---------------------------------------------------------------


async def test_customer_sees_own_bills_and_total_never_anothers(db_session: AsyncSession) -> None:
    mine, my_conn = await customer_with_bills(db_session)
    other, other_conn = await customer_with_bills(db_session)
    paid_at = datetime(2026, 9, 12, tzinfo=UTC)
    await make_bill(db_session, my_conn.id, period="2026-09", status="paid", paid_at=paid_at)
    await make_bill(db_session, my_conn.id, period="2026-10", amount_bdt=Decimal("1200.00"))
    await make_bill(db_session, my_conn.id, period="2026-11")
    await make_bill(db_session, other_conn.id, period="2026-11", amount_bdt=Decimal("777.00"))

    result = await run(db_session, mine, "get_my_bill_status")

    assert result["ok"] is True
    assert result["customer_code"] == my_conn.customer_code
    assert result["connection_status"] == "active"
    assert "customer_name" not in result
    assert [b["period"] for b in result["bills"]] == ["2026-11", "2026-10", "2026-09"]
    assert result["bills"][1] == {
        "period": "2026-10",
        "amount_bdt": "1200.00",
        "status": "unpaid",
        "due_date": "2026-12-10",
        "paid_at": None,
    }
    assert result["bills"][2]["paid_at"] == paid_at.isoformat()
    assert result["total_due_bdt"] == "2200.00"
    text = json.dumps(result)
    assert other_conn.customer_code not in text and "777.00" not in text


async def test_bill_status_returns_at_most_six_newest_bills(db_session: AsyncSession) -> None:
    mine, conn = await customer_with_bills(db_session)
    for month in range(1, 9):
        await make_bill(db_session, conn.id, period=f"2026-{month:02d}")

    result = await run(db_session, mine, "get_my_bill_status")

    assert [b["period"] for b in result["bills"]][::5] == ["2026-08", "2026-03"]
    assert len(result["bills"]) == 6
    assert result["total_due_bdt"] == "8000.00"


async def test_period_filter_and_missing_period(db_session: AsyncSession) -> None:
    mine, conn = await customer_with_bills(db_session)
    await make_bill(db_session, conn.id, period="2026-10")
    await make_bill(db_session, conn.id, period="2026-11")

    hit = await run(db_session, mine, "get_my_bill_status", '{"period": "2026-10"}')
    miss = await run(db_session, mine, "get_my_bill_status", '{"period": "2025-01"}')

    assert [b["period"] for b in hit["bills"]] == ["2026-10"]
    assert miss == {"ok": False, "error": "no_bill_for_period"}


async def test_customer_without_connection_gets_no_connection(db_session: AsyncSession) -> None:
    customer = await make_user(db_session, "customer")

    assert await run(db_session, customer, "get_my_bill_status") == {
        "ok": False,
        "error": "no_connection",
    }
    assert await run(db_session, customer, "get_my_area_status") == {
        "ok": False,
        "error": "no_connection",
    }


# --- lookup_customer_bills ------------------------------------------------------------


async def test_staff_lookup_by_customer_code_includes_name(db_session: AsyncSession) -> None:
    technician = await make_user(db_session, "technician")
    _, conn = await customer_with_bills(db_session)
    await make_bill(db_session, conn.id)

    result = await run(
        db_session,
        technician,
        "lookup_customer_bills",
        json.dumps({"customer_code": conn.customer_code}),
    )
    unknown = await run(
        db_session, technician, "lookup_customer_bills", '{"customer_code": "ND-999999"}'
    )

    assert result["ok"] is True
    assert result["customer_name"] == conn.customer_name
    assert result["total_due_bdt"] == "1000.00"
    assert unknown == {"ok": False, "error": "not_found"}


# --- area status ----------------------------------------------------------------------


async def test_customer_area_status_counts_and_active_notices(db_session: AsyncSession) -> None:
    area = await make_area(db_session)
    me = await make_user(db_session, "customer")
    neighbour = await make_user(db_session, "customer")
    admin = await make_user(db_session, "admin")
    mine = await make_connection(db_session, customer_user_id=me.id, area_id=area.id)
    theirs = await make_connection(db_session, customer_user_id=neighbour.id, area_id=area.id)
    far = await make_connection(db_session)  # another area: must not be counted
    now = datetime.now(UTC)
    await make_notice(db_session, area.id, admin.id, message_en="ACTIVE")
    await make_notice(
        db_session,
        area.id,
        admin.id,
        message_en="EXPIRED",
        starts_at=now - timedelta(hours=5),
        ends_at=now - timedelta(hours=1),
    )
    await make_notice(
        db_session,
        area.id,
        admin.id,
        message_en="FUTURE",
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
    )
    await make_complaint(db_session, mine.id, me.id, category="slow_speed")
    await make_complaint(db_session, theirs.id, neighbour.id, status="in_progress")
    await make_complaint(db_session, theirs.id, neighbour.id, status="resolved")
    await make_complaint(db_session, far.id, neighbour.id)

    result = await run(db_session, me, "get_my_area_status")

    assert result["area_code"] == area.code
    assert result["area_name_bn"] == area.name_bn
    assert [n["message_en"] for n in result["active_notices"]] == ["ACTIVE"]
    assert result["active_notices"][0]["message_bn"] == "ফাইবার কাটা পড়েছে।"
    assert set(result["active_notices"][0]) == {"kind", "message_bn", "message_en", "ends_at"}
    assert result["open_complaints_in_area"] == 2
    assert [(c["category"], c["status"]) for c in result["my_open_complaints"]] == [
        ("slow_speed", "open")
    ]


async def test_staff_area_status_by_category_and_oldest_age(db_session: AsyncSession) -> None:
    area = await make_area(db_session)
    empty_area = await make_area(db_session)
    technician = await make_user(db_session, "technician")
    customer = await make_user(db_session, "customer")
    conn = await make_connection(db_session, customer_user_id=customer.id, area_id=area.id)
    now = datetime.now(UTC)
    await make_complaint(
        db_session, conn.id, customer.id, created_at=now - timedelta(hours=5, minutes=30)
    )
    await make_complaint(db_session, conn.id, customer.id, status="in_progress")
    await make_complaint(db_session, conn.id, customer.id, category="slow_speed")
    await make_complaint(
        db_session, conn.id, customer.id, status="resolved", created_at=now - timedelta(hours=100)
    )

    result = await run(
        db_session, technician, "get_area_service_status", json.dumps({"area_code": area.code})
    )
    empty = await run(
        db_session,
        technician,
        "get_area_service_status",
        json.dumps({"area_code": empty_area.code}),
    )
    unknown = await run(db_session, technician, "get_area_service_status", '{"area_code": "NOPE"}')

    assert result["area_code"] == area.code
    assert result["open_complaints_by_category"] == {"no_internet": 2, "slow_speed": 1}
    assert result["oldest_open_complaint_hours"] == 5
    assert empty["open_complaints_by_category"] == {}
    assert empty["oldest_open_complaint_hours"] is None
    assert unknown == {"ok": False, "error": "unknown_area"}


# --- argument validation --------------------------------------------------------------


@pytest.mark.parametrize(
    ("tool", "args", "field", "secret"),
    [
        ("get_my_bill_status", "{not json", None, "not json"),
        ("get_my_bill_status", '{"period": "2026-13"}', "period", "2026-13"),
        (
            "get_my_bill_status",
            '{"period": "2026-11", "customer_code": "ND-123456"}',
            "customer_code",
            "ND-123456",
        ),
    ],
)
async def test_invalid_arguments_never_echo_values(
    db_session: AsyncSession, tool: str, args: str, field: str | None, secret: str
) -> None:
    customer = await make_user(db_session, "customer")
    outcome = await execute(db_session, customer, tool, args)
    body = json.loads(outcome.content)

    assert outcome.ok is False
    assert body["error"] == "invalid_arguments"
    assert (field in body["fields"]) if field else isinstance(body["fields"], list)
    assert secret not in outcome.content


async def test_bad_customer_code_is_invalid_arguments(db_session: AsyncSession) -> None:
    admin = await make_user(db_session, "admin")

    result = await run(db_session, admin, "lookup_customer_bills", '{"customer_code": "bad"}')

    assert result == {"ok": False, "error": "invalid_arguments", "fields": ["customer_code"]}


# --- limits ---------------------------------------------------------------------------


async def test_slow_handler_times_out(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def slow(*_: Any) -> dict[str, Any]:
        await asyncio.sleep(1)
        return {}

    name = "get_my_area_status"
    monkeypatch.setitem(REGISTRY, name, replace(REGISTRY[name], handler=slow))
    monkeypatch.setattr(registry, "TOOL_TIMEOUT_SECONDS", 0.01)
    customer = await make_user(db_session, "customer")

    assert await run(db_session, customer, name) == {"ok": False, "error": "timeout"}


async def test_oversized_result_is_replaced(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    customer, conn = await customer_with_bills(db_session)
    await make_bill(db_session, conn.id)
    monkeypatch.setattr(registry, "MAX_RESULT_BYTES", 50)

    result = await run(db_session, customer, "get_my_bill_status")

    assert result == {"ok": False, "error": "result_too_large"}


async def test_success_keeps_bangla_readable(db_session: AsyncSession) -> None:
    area = await make_area(db_session)
    customer = await make_user(db_session, "customer")
    await make_connection(db_session, customer_user_id=customer.id, area_id=area.id)

    outcome = await execute(db_session, customer, "get_my_area_status", "")

    assert outcome.ok is True
    assert area.name_bn in outcome.content  # not \u-escaped
