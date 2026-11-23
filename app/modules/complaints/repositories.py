"""SQL only. Every query takes the caller's Scope (CLAUDE.md)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams
from app.modules.auth.dependencies import Scope
from app.modules.complaints.models import Complaint
from app.modules.connections.models import Connection
from app.modules.users.models import Role, User


def _scope_filter(scope: Scope) -> list[ColumnElement[bool]]:
    # A complaint is visible through its connection: customers see only their own.
    return [] if scope.is_staff else [Connection.customer_user_id == scope.user_id]


async def list_complaints(
    session: AsyncSession,
    scope: Scope,
    page: PageParams,
    *,
    status: str | None,
    area_id: int | None,
) -> tuple[Sequence[Complaint], int]:
    conditions = _scope_filter(scope)
    if status is not None:
        conditions.append(Complaint.status == status)
    if area_id is not None:
        conditions.append(Connection.area_id == area_id)

    rows = await session.execute(
        select(Complaint)
        .join(Connection, Complaint.connection_id == Connection.id)
        .where(*conditions)
        .order_by(Complaint.created_at.desc(), Complaint.id)  # id breaks ties between pages
        .limit(page.limit)
        .offset(page.offset)
    )
    total = await session.execute(
        select(func.count())
        .select_from(Complaint)
        .join(Connection, Complaint.connection_id == Connection.id)
        .where(*conditions)
    )
    return rows.scalars().all(), total.scalar_one()


async def get_complaint(
    session: AsyncSession, scope: Scope, complaint_id: uuid.UUID
) -> Complaint | None:
    query = (
        select(Complaint)
        .join(Connection, Complaint.connection_id == Connection.id)
        .where(Complaint.id == complaint_id, *_scope_filter(scope))
    )
    return (await session.execute(query)).scalar_one_or_none()


async def technician_exists(session: AsyncSession, scope: Scope, user_id: uuid.UUID) -> bool:
    query = select(
        exists().where(
            User.id == user_id,
            User.is_active.is_(True),
            User.role_id == Role.id,
            Role.name == "technician",
        )
    )
    return bool((await session.execute(query)).scalar())
