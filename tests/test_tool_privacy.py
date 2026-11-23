"""Data sent to the LLM provider (PROPOSAL §10.2 last row): tool results go to an external
model, so they must never hold a phone number or an address, for any tool or role."""

import json
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent.registry import execute
from app.modules.areas.models import Area
from tests.factories import make_bill, make_complaint, make_connection, make_notice, make_user

PHONE = "+8801987654321"
ADDRESS = "House 77, Secret Lane"
FORBIDDEN_KEYS = {"phone", "address", "email", "password_hash"}


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


@pytest.mark.parametrize(
    ("role", "tool", "args"),
    [
        ("customer", "get_my_bill_status", {}),
        ("customer", "get_my_area_status", {}),
        ("technician", "lookup_customer_bills", {"customer_code": "CODE"}),
        ("technician", "get_area_service_status", {"area_code": "AREA"}),
    ],
)
async def test_tool_output_has_no_phone_or_address(
    db_session: AsyncSession, role: str, tool: str, args: dict[str, str]
) -> None:
    customer = await make_user(db_session, "customer")
    conn = await make_connection(
        db_session, customer_user_id=customer.id, phone=PHONE, address=ADDRESS
    )
    await make_bill(db_session, conn.id)
    await make_complaint(db_session, conn.id, customer.id)
    await make_notice(db_session, conn.area_id, customer.id)
    caller = customer if role == "customer" else await make_user(db_session, role)
    area = await db_session.get(Area, conn.area_id)
    assert area is not None
    area_code = area.code
    args = {k: {"CODE": conn.customer_code, "AREA": area_code}[v] for k, v in args.items()}

    outcome = await execute(db_session, caller, tool, json.dumps(args))
    payload = json.loads(outcome.content)

    assert outcome.ok is True, payload
    assert not (_keys(payload) & FORBIDDEN_KEYS)
    assert PHONE not in outcome.content and "1987654321" not in outcome.content
    assert ADDRESS not in outcome.content
