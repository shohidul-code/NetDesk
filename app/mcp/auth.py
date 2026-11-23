"""Staff-only JWT check in front of /mcp (PROPOSAL §9.7).

A pure ASGI wrapper, because the MCP server is not a FastAPI route and cannot use
Depends(get_current_user). It applies the same rules: Bearer token, signature and expiry,
then the user and role loaded from the database. Errors use our envelope (401, 403).
The Scope goes into a context variable that the tools read; the HTTP app runs in
stateless mode, so each request's tools run inside that request's context.
"""

import jwt
from starlette.types import ASGIApp, Receive, Send
from starlette.types import Scope as AsgiScope

from app.core.errors import AppError, ForbiddenError, UnauthorizedError, error_response
from app.core.security import decode_access_token
from app.mcp import server
from app.modules.auth.dependencies import Scope
from app.modules.users import repositories as users


async def staff_scope_from_token(authorization: str | None) -> Scope:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Not signed in.")
    try:
        user_id = decode_access_token(authorization[7:].strip())
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Your session is invalid or has expired.") from exc
    async with server.open_session() as session:
        user = await users.get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Your session is invalid or has expired.")
    scope = Scope(user_id=user.id, role=user.role.name)  # type: ignore[arg-type]
    if not scope.is_staff:
        raise ForbiddenError("MCP is for staff only.")
    return scope


class StaffJWTMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: AsgiScope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
        try:
            caller = await staff_scope_from_token(headers.get("authorization"))
        except AppError as exc:
            response = error_response(
                exc.status_code, exc.code, exc.message, exc.details, exc.headers
            )
            await response(scope, receive, send)
            return
        token = server.current_scope.set(caller)
        try:
            await self.app(scope, receive, send)
        finally:
            server.current_scope.reset(token)
