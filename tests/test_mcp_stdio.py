"""MCP over stdio (PROPOSAL §9.7): the installed `netdesk-mcp` script acts as the active
staff user in MCP_STDIO_USER_EMAIL, refuses anyone else, and keeps stdout for the
protocol (logs go to stderr)."""

import os
import subprocess
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from app.modules.users.models import User
from tests.conftest import REPO_ROOT

# The console script uv installed next to this interpreter (proves [project.scripts] works).
SCRIPT = str(Path(sys.executable).parent / "netdesk-mcp")
CommittedUser = Callable[[str], Awaitable[User]]


def _env(email: str) -> dict[str, str]:
    return {**os.environ, "MCP_STDIO_USER_EMAIL": email}


async def test_stdio_server_lists_and_calls_as_the_configured_staff_user(
    committed_user: CommittedUser,
) -> None:
    staff = await committed_user("admin")
    params = StdioServerParameters(command=SCRIPT, env=_env(staff.email), cwd=REPO_ROOT)

    async with Client(params) as client:
        tools = {t.name for t in (await client.list_tools()).tools}
        unknown = await client.call_tool("lookup_customer_bills", {"customer_code": "ND-999999"})
        resources = {str(r.uri) for r in (await client.list_resources()).resources}

    assert tools == {"lookup_customer_bills", "get_area_service_status"}
    assert resources == {"netdesk://packages/active"}
    assert unknown.is_error is True
    assert "Connection not found" in unknown.content[0].text  # type: ignore[union-attr]


def _start(email: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [SCRIPT],
        env=_env(email),
        cwd=REPO_ROOT,
        input="",
        capture_output=True,
        text=True,
        timeout=60,
    )


async def test_unknown_email_exits_before_serving() -> None:
    result = _start("nobody@netdesk.invalid")

    assert result.returncode == 1
    assert result.stdout == ""  # stdout belongs to the protocol, even on failure
    assert "MCP_STDIO_USER_EMAIL" in result.stderr


async def test_customer_email_is_refused(committed_user: CommittedUser) -> None:
    customer = await committed_user("customer")

    result = _start(customer.email)

    assert result.returncode == 1
    assert result.stdout == ""
