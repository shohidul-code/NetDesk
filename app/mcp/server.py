"""The MCP server (PROPOSAL §9.7): 2 tools, 1 resource and 1 prompt for staff.

Read-only, and every capability calls the same services as REST and the chat tools, so
no access rule is written twice. The caller's Scope arrives in a context variable set by
the transport: the JWT middleware for HTTP (app/mcp/auth.py), startup for stdio.
"""

import json
from collections.abc import Callable, Iterator
from contextlib import AbstractAsyncContextManager, contextmanager
from contextvars import ContextVar
from datetime import date
from typing import Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.core.errors import AppError
from app.modules.agent import tools
from app.modules.agent.schemas import GetAreaServiceStatusArgs, LookupCustomerBillsArgs
from app.modules.auth.dependencies import Scope
from app.modules.packages import services as packages
from app.modules.packages.schemas import PackageRead

current_scope: ContextVar[Scope | None] = ContextVar("mcp_scope", default=None)


def _default_session() -> AbstractAsyncContextManager[AsyncSession]:
    return get_sessionmaker()()


# Tests swap this for the test transaction, as they override get_session for REST.
open_session: Callable[[], AbstractAsyncContextManager[AsyncSession]] = _default_session

mcp = MCPServer(
    name="NetDesk",
    instructions="Read-only staff tools for a small Bangladeshi ISP: customer bills, "
    "area service status, active packages and a due-bill reminder template.",
)


def _staff_scope() -> Scope:
    """Defence in depth: the HTTP middleware already refuses non-staff, but no tool runs
    without a staff scope, whatever transport called it."""
    scope = current_scope.get()
    if scope is None or not scope.is_staff:
        raise ToolError("Staff only.")
    return scope


@contextmanager
def _as_tool_errors() -> Iterator[None]:
    """Our errors become ToolError, whose message reaches the client. Anything else
    becomes the SDK's generic error, so no traceback or SQL ever leaves the server."""
    try:
        yield
    except AppError as exc:
        raise ToolError(exc.message) from exc
    except ValidationError as exc:
        fields = ", ".join(str(e["loc"][0]) for e in exc.errors() if e["loc"])
        raise ToolError(f"Invalid arguments: {fields}.") from exc


@mcp.tool(description=tools.LOOKUP_CUSTOMER_BILLS_DESCRIPTION)
async def lookup_customer_bills(customer_code: str, period: str | None = None) -> dict[str, Any]:
    with _as_tool_errors():
        scope = _staff_scope()
        args = LookupCustomerBillsArgs(customer_code=customer_code, period=period)
        async with open_session() as session:
            return await tools.lookup_customer_bills(session, scope, args)


@mcp.tool(description=tools.GET_AREA_SERVICE_STATUS_DESCRIPTION)
async def get_area_service_status(area_code: str) -> dict[str, Any]:
    with _as_tool_errors():
        scope = _staff_scope()
        args = GetAreaServiceStatusArgs(area_code=area_code)
        async with open_session() as session:
            return await tools.get_area_service_status(session, scope, args)


@mcp.resource(
    "netdesk://packages/active",
    name="active_packages",
    description="Active internet packages with speed and monthly price in taka.",
    mime_type="application/json",
)
async def active_packages() -> str:
    with _as_tool_errors():
        scope = _staff_scope()
        async with open_session() as session:
            rows = await packages.list_packages(session, scope, active=True)
    data = [PackageRead.model_validate(p).model_dump(mode="json") for p in rows]
    return json.dumps(data, ensure_ascii=False)


def _long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%B %Y}"


@mcp.prompt(
    description="A polite due-bill reminder for one customer, with the real amount due. "
    "It only returns text; nothing is sent."
)
async def due_bill_reminder(customer_code: str, language: Literal["bn", "en"] = "bn") -> str:
    with _as_tool_errors():
        scope = _staff_scope()
        args = LookupCustomerBillsArgs(customer_code=customer_code)
        async with open_session() as session:
            status = await tools.lookup_customer_bills(session, scope, args)
    name, due, isp = status["customer_name"], status["total_due_bdt"], get_settings().operator_name
    unpaid = [b["due_date"] for b in status["bills"] if b["status"] == "unpaid"]
    if not unpaid:
        if language == "en":
            return f"Dear {name}, nothing is due on your internet account. Thank you, {isp}."
        return f"প্রিয় {name}, আপনার ইন্টারনেট বিলে কোনো বকেয়া নেই। ধন্যবাদ, {isp}।"
    by = _long_date(min(unpaid))  # the oldest unpaid bill; may already be past
    if language == "en":
        return (
            f"Dear {name}, your internet bill has ৳{due} due (due date: {by}). Please pay "
            f"with bKash, Nagad or at the office, and keep the TrxID. Thank you, {isp}."
        )
    return (
        f"প্রিয় {name}, আপনার ইন্টারনেট বিলের মোট বকেয়া ৳{due} (শেষ তারিখ: {by})। অনুগ্রহ করে "
        f"bKash, Nagad অথবা অফিসে পরিশোধ করুন এবং TrxID রেখে দিন। ধন্যবাদ, {isp}।"
    )
