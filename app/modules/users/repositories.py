"""SQL for users. Lookups by id and email, the role lookup and the registration claim
lookup are used before a Scope exists, so they take no scope."""

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams
from app.modules.connections.models import Connection
from app.modules.users.models import Role, RoleName, User

if TYPE_CHECKING:
    # auth.dependencies imports this module, so a real import here would be circular.
    from app.modules.auth.dependencies import Scope


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    query = select(User).where(User.email == email.lower())
    return (await session.execute(query)).scalar_one_or_none()


async def get_role(session: AsyncSession, name: str) -> Role:
    return (await session.execute(select(Role).where(Role.name == name))).scalar_one()


async def find_connection_to_claim(
    session: AsyncSession, customer_code: str, phone: str
) -> Connection | None:
    """Used by registration, before the caller has an account or a Scope. The row is
    locked so two people cannot claim the same connection at once."""
    query = (
        select(Connection)
        .where(Connection.customer_code == customer_code, Connection.phone == phone)
        .with_for_update()
    )
    return (await session.execute(query)).scalar_one_or_none()


async def list_users(
    session: AsyncSession, scope: "Scope", page: PageParams, role: RoleName | None
) -> tuple[Sequence[User], int]:
    conditions = [Role.name == role] if role else []
    query = (
        select(User)
        .join(Role)
        .where(*conditions)
        .order_by(User.created_at, User.id)
        .limit(page.limit)
        .offset(page.offset)
    )
    total = select(func.count()).select_from(User).join(Role).where(*conditions)
    items = (await session.execute(query)).scalars().all()
    return items, (await session.execute(total)).scalar_one()


async def get_user(session: AsyncSession, scope: "Scope", user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def count_active_admins(session: AsyncSession, scope: "Scope") -> int:
    query = (
        select(func.count())
        .select_from(User)
        .join(Role)
        .where(Role.name == "admin", User.is_active)
    )
    return (await session.execute(query)).scalar_one()
