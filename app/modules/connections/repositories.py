"""SQL only. Every query takes the caller's Scope (CLAUDE.md)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams
from app.modules.areas.models import Area
from app.modules.auth.dependencies import Scope
from app.modules.billing.models import Bill
from app.modules.complaints.models import Complaint
from app.modules.connections.models import Connection
from app.modules.packages.models import Package

SORT_COLUMNS = {
    "customer_code": Connection.customer_code,
    "customer_name": Connection.customer_name,
    "created_at": Connection.created_at,
}


def _scope_filter(scope: Scope) -> list[ColumnElement[bool]]:
    # Customers see only their own connection; staff see all.
    return [] if scope.is_staff else [Connection.customer_user_id == scope.user_id]


def _escape_like(text: str) -> str:
    """Make %, _ and the escape character match themselves, not act as wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def list_connections(
    session: AsyncSession,
    scope: Scope,
    page: PageParams,
    *,
    area_id: int | None,
    status: str | None,
    package_id: int | None,
    q: str | None,
    sort: str,
) -> tuple[Sequence[Connection], int]:
    conditions = _scope_filter(scope)
    if area_id is not None:
        conditions.append(Connection.area_id == area_id)
    if status is not None:
        conditions.append(Connection.status == status)
    if package_id is not None:
        conditions.append(Connection.package_id == package_id)
    if q:
        pattern = f"%{_escape_like(q)}%"
        conditions.append(
            Connection.customer_code.ilike(pattern, escape="\\")
            | Connection.customer_name.ilike(pattern, escape="\\")
            | Connection.phone.ilike(pattern, escape="\\")
        )

    column = SORT_COLUMNS[sort.lstrip("-")]
    order = column.desc() if sort.startswith("-") else column.asc()
    rows = await session.execute(
        select(Connection)
        .where(*conditions)
        .order_by(order, Connection.id)  # id breaks ties so pages never overlap
        .limit(page.limit)
        .offset(page.offset)
    )
    total = await session.execute(select(func.count()).select_from(Connection).where(*conditions))
    return rows.scalars().all(), total.scalar_one()


async def get_connection(
    session: AsyncSession, scope: Scope, connection_id: uuid.UUID
) -> Connection | None:
    query = select(Connection).where(Connection.id == connection_id, *_scope_filter(scope))
    return (await session.execute(query)).scalar_one_or_none()


async def code_taken(session: AsyncSession, scope: Scope, customer_code: str) -> bool:
    query = select(exists().where(Connection.customer_code == customer_code))
    return bool((await session.execute(query)).scalar())


async def area_exists(session: AsyncSession, scope: Scope, area_id: int) -> bool:
    return bool((await session.execute(select(exists().where(Area.id == area_id)))).scalar())


async def package_exists(session: AsyncSession, scope: Scope, package_id: int) -> bool:
    query = select(exists().where(Package.id == package_id))
    return bool((await session.execute(query)).scalar())


async def has_history(session: AsyncSession, scope: Scope, connection_id: uuid.UUID) -> bool:
    """Bills or complaints reference the connection, so deleting it would lose records."""
    query = select(
        exists().where(Bill.connection_id == connection_id)
        | exists().where(Complaint.connection_id == connection_id)
    )
    return bool((await session.execute(query)).scalar())
