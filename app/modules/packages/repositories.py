"""SQL only. Every query takes the caller's Scope (CLAUDE.md)."""

from collections.abc import Sequence

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import Scope
from app.modules.connections.models import Connection
from app.modules.packages.models import Package


async def list_packages(
    session: AsyncSession, scope: Scope, active: bool | None
) -> Sequence[Package]:
    query = select(Package).order_by(Package.monthly_price_bdt, Package.name)
    if not scope.is_staff:
        active = True  # customers see only plans they can buy (PROPOSAL §7.3)
    if active is not None:
        query = query.where(Package.is_active.is_(active))
    return (await session.execute(query)).scalars().all()


async def get_package(session: AsyncSession, scope: Scope, package_id: int) -> Package | None:
    return await session.get(Package, package_id)


async def name_taken(session: AsyncSession, scope: Scope, name: str, exclude_id: int = 0) -> bool:
    query = select(exists().where(Package.name == name, Package.id != exclude_id))
    return bool((await session.execute(query)).scalar())


async def package_in_use(session: AsyncSession, scope: Scope, package_id: int) -> bool:
    query = select(exists().where(Connection.package_id == package_id))
    return bool((await session.execute(query)).scalar())
