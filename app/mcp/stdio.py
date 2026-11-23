"""`netdesk-mcp`: the MCP server over stdio for a local AI client (PROPOSAL §9.7).

There is no token on stdio, so the caller is fixed at startup: MCP_STDIO_USER_EMAIL must
be an active technician or admin, or the process exits with code 1 before serving.
stdout carries the protocol, so logs go to stderr only (configure_logging does that).
"""

import asyncio
import logging
import sys

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.mcp import server
from app.modules.auth.dependencies import Scope
from app.modules.users import repositories as users

log = logging.getLogger("netdesk.mcp.stdio")


class StdioUserError(Exception):
    pass


async def resolve_staff(email: str) -> Scope:
    async with server.open_session() as session:
        user = await users.get_user_by_email(session, email)
    if user is None or not user.is_active:
        raise StdioUserError(f"MCP_STDIO_USER_EMAIL={email} is not an active user.")
    scope = Scope(user_id=user.id, role=user.role.name)  # type: ignore[arg-type]
    if not scope.is_staff:
        raise StdioUserError(f"MCP_STDIO_USER_EMAIL={email} is not staff.")
    return scope


async def run() -> None:
    # Set before serving: the tasks the server starts copy this context.
    server.current_scope.set(await resolve_staff(get_settings().mcp_stdio_user_email))
    await server.mcp.run_stdio_async()


def main() -> None:
    configure_logging()
    try:
        asyncio.run(run())
    except StdioUserError as exc:
        log.error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
