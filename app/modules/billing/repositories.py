"""SQL only. Every query takes the caller's Scope (CLAUDE.md)."""

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, String, exists, func, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.areas.models import Area
from app.modules.auth.dependencies import Scope
from app.modules.billing.models import Bill
from app.modules.connections.models import Connection
from app.modules.packages.models import Package


def _scoped(query: Any, scope: Scope) -> Any:
    """A customer sees only bills of their own connections. Staff see all."""
    if scope.is_staff:
        return query
    return query.where(Connection.customer_user_id == scope.user_id)


async def count_billable_connections(session: AsyncSession, scope: Scope) -> int:
    query = select(func.count()).select_from(Connection).where(Connection.status != "disconnected")
    return (await session.execute(query)).scalar_one()


async def insert_bills(session: AsyncSession, scope: Scope, period: str, due_date: date) -> int:
    """One bill per billable connection; existing (connection, period) pairs are skipped.
    Returns how many were really created."""
    billable = (
        select(
            Connection.id,
            literal(period, String),
            Package.monthly_price_bdt,
            literal(due_date, Date),
        )
        .join(Package, Package.id == Connection.package_id)
        .where(Connection.status != "disconnected")
    )
    statement = (
        insert(Bill)
        # include_defaults=False: let the database make each id (a Python uuid4 default
        # would run once for the whole statement).
        .from_select(
            ["connection_id", "period", "amount_bdt", "due_date"], billable, include_defaults=False
        )
        .on_conflict_do_nothing(index_elements=["connection_id", "period"])
        .returning(Bill.id)
    )
    return len((await session.execute(statement)).all())


async def list_bills(
    session: AsyncSession,
    scope: Scope,
    *,
    connection_id: uuid.UUID | None,
    period: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[Sequence[Bill], int]:
    query = _scoped(select(Bill).join(Connection, Connection.id == Bill.connection_id), scope)
    if connection_id is not None:
        query = query.where(Bill.connection_id == connection_id)
    if period is not None:
        query = query.where(Bill.period == period)
    if status is not None:
        query = query.where(Bill.status == status)
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    page = query.order_by(Bill.period.desc(), Bill.connection_id).limit(limit).offset(offset)
    return (await session.execute(page)).scalars().all(), total


async def get_bill_for_update(
    session: AsyncSession, scope: Scope, bill_id: uuid.UUID
) -> Bill | None:
    """Locks the row so two payments for one bill cannot both succeed."""
    query = select(Bill).join(Connection, Connection.id == Bill.connection_id)
    query = _scoped(query, scope).where(Bill.id == bill_id).with_for_update(of=Bill)
    return (await session.execute(query)).scalar_one_or_none()


async def trx_id_used(session: AsyncSession, scope: Scope, trx_id: str) -> bool:
    query = select(exists().where(Bill.trx_id == trx_id))
    return bool((await session.execute(query)).scalar())


async def unpaid_by_area(session: AsyncSession, scope: Scope, period: str) -> Sequence[Any]:
    query = (
        select(
            Area.id.label("area_id"),
            Area.code.label("area_code"),
            func.count(Bill.id).label("unpaid_count"),
            func.coalesce(func.sum(Bill.amount_bdt), Decimal(0)).label("unpaid_total_bdt"),
        )
        .select_from(Bill)
        .join(Connection, Connection.id == Bill.connection_id)
        .join(Area, Area.id == Connection.area_id)
        .where(Bill.period == period, Bill.status == "unpaid")
        .group_by(Area.id, Area.code)
        .order_by(Area.code)
    )
    return (await session.execute(_scoped(query, scope))).all()
