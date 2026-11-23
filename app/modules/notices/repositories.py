"""SQL only. Every query takes the caller's Scope (CLAUDE.md)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import and_, exists, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.areas.models import Area
from app.modules.auth.dependencies import Scope
from app.modules.connections.models import Connection
from app.modules.notices.models import AreaNotice


async def list_notices(
    session: AsyncSession, scope: Scope, area_id: int | None, active: bool | None
) -> Sequence[AreaNotice]:
    query = select(AreaNotice).order_by(AreaNotice.starts_at.desc())
    if not scope.is_staff:
        # A customer sees notices only for the areas of their own connections.
        own_areas = select(Connection.area_id).where(Connection.customer_user_id == scope.user_id)
        query = query.where(AreaNotice.area_id.in_(own_areas))
    if area_id is not None:
        query = query.where(AreaNotice.area_id == area_id)
    if active is not None:
        is_active = and_(AreaNotice.starts_at <= func.now(), func.now() < AreaNotice.ends_at)
        query = query.where(is_active if active else not_(is_active))
    return (await session.execute(query)).scalars().all()


async def get_notice(
    session: AsyncSession, scope: Scope, notice_id: uuid.UUID
) -> AreaNotice | None:
    return await session.get(AreaNotice, notice_id)


async def area_exists(session: AsyncSession, scope: Scope, area_id: int) -> bool:
    return bool((await session.execute(select(exists().where(Area.id == area_id)))).scalar())
