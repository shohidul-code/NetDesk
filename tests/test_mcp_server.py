"""MCP server capabilities in-process (PROPOSAL §9.7): 2 tools, 1 resource, 1 prompt, all
calling the same services as REST and chat. Transport and auth are tested separately."""

import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp import server
from app.modules.auth.dependencies import Scope
from app.modules.billing import services as billing
from app.modules.users.models import User
from tests.factories import (
    make_area,
    make_bill,
    make_connection,
    make_notice,
    make_package,
    make_user,
)

SetUser = Callable[[User | None], None]


@pytest.fixture
def mcp_as(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> SetUser:
    """Tools use the test transaction, and the caller is whoever the test sets."""

    @asynccontextmanager
    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    monkeypatch.setattr(server, "open_session", test_session)
    # A fresh variable per test: pytest-asyncio tears down in another context, so a
    # reset token would not apply there.
    scope_var: ContextVar[Scope | None] = ContextVar("test_scope", default=None)
    monkeypatch.setattr(server, "current_scope", scope_var)

    def set_user(user: User | None) -> None:
        scope = None if user is None else Scope(user_id=user.id, role=user.role.name)  # type: ignore[arg-type]
        scope_var.set(scope)

    return set_user


async def test_exposes_two_tools_one_resource_one_prompt() -> None:
    tools = {t.name for t in await server.mcp.list_tools()}
    resources = {str(r.uri) for r in await server.mcp.list_resources()}
    prompts = {p.name for p in await server.mcp.list_prompts()}

    assert tools == {"lookup_customer_bills", "get_area_service_status"}
    assert resources == {"netdesk://packages/active"}
    assert prompts == {"due_bill_reminder"}


async def test_lookup_returns_what_the_billing_service_returns(
    db_session: AsyncSession, admin: User, mcp_as: SetUser
) -> None:
    conn = await make_connection(db_session)
    await make_bill(db_session, conn.id)
    mcp_as(admin)

    result = await server.mcp.call_tool(
        "lookup_customer_bills", {"customer_code": conn.customer_code}
    )
    direct = await billing.bill_status(
        db_session, Scope(user_id=admin.id, role="admin"), customer_code=conn.customer_code
    )

    assert result.is_error is False
    assert result.structured_content == direct
    assert direct["total_due_bdt"] == "1000.00"


async def test_unknown_customer_and_bad_code_are_clear_tool_errors(
    db_session: AsyncSession, admin: User, mcp_as: SetUser
) -> None:
    mcp_as(admin)

    with pytest.raises(ToolError, match="Connection not found"):
        await server.mcp.call_tool("lookup_customer_bills", {"customer_code": "ND-999999"})
    with pytest.raises(ToolError, match="customer_code"):
        await server.mcp.call_tool("lookup_customer_bills", {"customer_code": "DROP TABLE"})


async def test_area_status_for_staff(
    db_session: AsyncSession, admin: User, mcp_as: SetUser
) -> None:
    technician = await make_user(db_session, "technician")
    area = await make_area(db_session)
    await make_notice(db_session, area.id, admin.id)
    mcp_as(technician)

    result = await server.mcp.call_tool("get_area_service_status", {"area_code": area.code})

    assert result.is_error is False
    assert result.structured_content is not None
    assert len(result.structured_content["active_notices"]) == 1


async def test_packages_resource_lists_only_active_packages(
    db_session: AsyncSession, admin: User, mcp_as: SetUser
) -> None:
    active = await make_package(db_session)
    retired = await make_package(db_session, is_active=False)
    mcp_as(admin)

    contents = list(await server.mcp.read_resource("netdesk://packages/active"))  # type: ignore[arg-type]
    names = {p["name"] for p in json.loads(str(contents[0].content))}

    assert contents[0].mime_type == "application/json"
    assert active.name in names
    assert retired.name not in names


async def test_due_bill_reminder_uses_the_real_due_amount(
    db_session: AsyncSession, admin: User, mcp_as: SetUser
) -> None:
    conn = await make_connection(db_session)
    await make_bill(db_session, conn.id, amount_bdt=Decimal("800.00"))
    mcp_as(admin)

    bn = await server.mcp.get_prompt("due_bill_reminder", {"customer_code": conn.customer_code})
    en = await server.mcp.get_prompt(
        "due_bill_reminder", {"customer_code": conn.customer_code, "language": "en"}
    )
    bn_text = bn.messages[0].content.text  # type: ignore[union-attr]
    en_text = en.messages[0].content.text  # type: ignore[union-attr]

    assert "৳800.00" in bn_text and conn.customer_name in bn_text
    assert "৳800.00" in en_text and "10 December 2026" in en_text


async def test_reminder_for_a_customer_with_nothing_due(
    db_session: AsyncSession, admin: User, mcp_as: SetUser
) -> None:
    conn = await make_connection(db_session)
    await make_bill(db_session, conn.id, status="paid", paid_at=datetime.now(UTC))
    mcp_as(admin)

    result = await server.mcp.get_prompt(
        "due_bill_reminder", {"customer_code": conn.customer_code, "language": "en"}
    )

    assert "nothing is due" in result.messages[0].content.text  # type: ignore[union-attr]


@pytest.mark.parametrize("role", [None, "customer"])
async def test_non_staff_callers_are_refused_inside_the_server(
    db_session: AsyncSession, mcp_as: SetUser, role: str | None
) -> None:
    """Defence in depth: the HTTP middleware already refuses them, but a tool never runs
    without a staff scope, whatever transport called it."""
    conn = await make_connection(db_session)
    mcp_as(None if role is None else await make_user(db_session, role))

    with pytest.raises(ToolError, match="Staff only"):
        await server.mcp.call_tool("lookup_customer_bills", {"customer_code": conn.customer_code})
