"""Business rules for packages. Services own the transaction and call commit."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.modules.auth.dependencies import Scope
from app.modules.packages import repositories
from app.modules.packages.models import Package
from app.modules.packages.schemas import PackageCreate, PackageUpdate


async def list_packages(
    session: AsyncSession, scope: Scope, active: bool | None
) -> Sequence[Package]:
    return await repositories.list_packages(session, scope, active)


async def _get_or_404(session: AsyncSession, scope: Scope, package_id: int) -> Package:
    package = await repositories.get_package(session, scope, package_id)
    if package is None:
        raise NotFoundError("Package not found.")
    return package


async def create_package(session: AsyncSession, scope: Scope, data: PackageCreate) -> Package:
    if await repositories.name_taken(session, scope, data.name):
        raise ConflictError("A package with this name already exists.")
    package = Package(**data.model_dump())
    session.add(package)
    await session.commit()
    return package


async def update_package(
    session: AsyncSession, scope: Scope, package_id: int, data: PackageUpdate
) -> Package:
    package = await _get_or_404(session, scope, package_id)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and await repositories.name_taken(
        session, scope, changes["name"], exclude_id=package_id
    ):
        raise ConflictError("A package with this name already exists.")
    for field, value in changes.items():
        setattr(package, field, value)
    await session.commit()
    return package


async def delete_package(session: AsyncSession, scope: Scope, package_id: int) -> None:
    package = await _get_or_404(session, scope, package_id)
    if await repositories.package_in_use(session, scope, package_id):
        raise ConflictError("This package is in use. Set it inactive instead.")
    await session.delete(package)
    await session.commit()
