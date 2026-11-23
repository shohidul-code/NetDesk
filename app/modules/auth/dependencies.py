"""Who is calling, and what they may see.

Phase 2 STUB: `get_current_user` returns the first active admin, so every route can
already declare its access rules. Phase 3 replaces only this function with JWT
validation (PROPOSAL §16, Phase 2); routes and `require_roles` stay the same.
Keep the name `get_current_user`: tests/test_rubric_rules.py looks for it on routes.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import ForbiddenError, UnauthorizedError
from app.modules.users.models import Role, RoleName, User


async def get_current_user(session: Annotated[AsyncSession, Depends(get_session)]) -> User:
    # shortcut: no token check yet; acts as the first active admin until Phase 3 adds JWT.
    user = (
        await session.execute(
            select(User)
            .join(Role)
            .where(Role.name == "admin", User.is_active.is_(True))
            .order_by(User.created_at)
            .limit(1)
        )
    ).scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("Not signed in.")
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
