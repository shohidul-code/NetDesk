"""SQL for users. Lookups by id and email are used by authentication itself, before a
Scope exists, so these two take no scope."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    query = select(User).where(User.email == email.lower())
    return (await session.execute(query)).scalar_one_or_none()
