"""Who is calling, and what they may see.

`get_current_user` reads the Bearer token, checks its signature and expiry, then loads
the user and role from the database on every request (CLAUDE.md). Keep the name:
tests/test_rubric_rules.py checks that every non-public route depends on it.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.modules.users import repositories as users
from app.modules.users.models import RoleName, User

# auto_error=False: a missing token becomes our 401 envelope, not FastAPI's default body.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if token is None:
        raise UnauthorizedError("Not signed in.")
    try:
        user_id = decode_access_token(token)
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Your session is invalid or has expired.") from exc
    user = await users.get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Your session is invalid or has expired.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass(frozen=True)
class Scope:
    """What every repository query filters by (CLAUDE.md). Customers see only their own
    connections, bills and complaints; staff see everything."""

    user_id: uuid.UUID
    role: RoleName

    @property
    def is_staff(self) -> bool:
        return self.role in ("admin", "technician")


async def get_scope(user: CurrentUser) -> Scope:
    return Scope(user_id=user.id, role=user.role.name)  # type: ignore[arg-type]


CurrentScope = Annotated[Scope, Depends(get_scope)]


def require_roles(*roles: RoleName) -> Callable[[User], Awaitable[User]]:
    """Dependency factory: `Depends(require_roles("admin"))`. Other roles get 403."""

    async def check(user: CurrentUser) -> User:
        if user.role.name not in roles:
            raise ForbiddenError("Your role cannot do this.")
        return user

    return check
