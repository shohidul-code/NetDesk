"""SQL only. Every query takes the caller's Scope (CLAUDE.md)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import and_, exists, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.areas.models import Area
from app.modules.auth.dependencies import Scope
from app.modules.complaints.models import Complaint
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


OPEN_STATUSES = ("open", "in_progress")


async def find_area_for_status(
    session: AsyncSession, scope: Scope, area_code: str | None
) -> Area | None:
    """Staff: the area with this code. Customer: the area of their own connection
    (lowest customer code if several)."""
    if scope.is_staff:
        return (
            await session.execute(select(Area).where(Area.code == area_code))
        ).scalar_one_or_none()
    query = (
        select(Area)
        .join(Connection, Connection.area_id == Area.id)
        .where(Connection.customer_user_id == scope.user_id)
        .order_by(Connection.customer_code)
        .limit(1)
    )
    return (await session.execute(query)).scalar_one_or_none()


async def active_notices(session: AsyncSession, scope: Scope, area_id: int) -> Sequence[AreaNotice]:
    query = (
        select(AreaNotice)
        .where(AreaNotice.area_id == area_id)
        .where(AreaNotice.starts_at <= func.now(), func.now() < AreaNotice.ends_at)
        .order_by(AreaNotice.starts_at.desc())
    )
    return (await session.execute(query)).scalars().all()


def _open_in_area(area_id: int) -> Any:
    return (
        select(Complaint)
        .join(Connection, Connection.id == Complaint.connection_id)
        .where(Connection.area_id == area_id, Complaint.status.in_(OPEN_STATUSES))
    )


async def open_complaint_count(session: AsyncSession, scope: Scope, area_id: int) -> int:
    query = select(func.count()).select_from(_open_in_area(area_id).subquery())
    return (await session.execute(query)).scalar_one()


async def my_open_complaints(session: AsyncSession, scope: Scope) -> Sequence[Complaint]:
    query = (
        select(Complaint)
        .join(Connection, Connection.id == Complaint.connection_id)
        .where(Connection.customer_user_id == scope.user_id, Complaint.status.in_(OPEN_STATUSES))
        .order_by(Complaint.created_at.desc())
    )
    return (await session.execute(query)).scalars().all()


async def open_complaints_by_category(
    session: AsyncSession, scope: Scope, area_id: int
) -> dict[str, int]:
    sub = _open_in_area(area_id).subquery()
    query = select(sub.c.category, func.count()).group_by(sub.c.category).order_by(sub.c.category)
    return {category: count for category, count in (await session.execute(query)).all()}


async def oldest_open_complaint_at(
    session: AsyncSession, scope: Scope, area_id: int
) -> datetime | None:
    sub = _open_in_area(area_id).subquery()
    oldest: datetime | None = (
        await session.execute(select(func.min(sub.c.created_at)))
    ).scalar_one()
    return oldest
