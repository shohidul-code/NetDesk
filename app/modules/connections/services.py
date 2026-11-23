"""Business rules for connections. Services own the transaction and call commit."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.pagination import Page, PageParams
from app.modules.auth.dependencies import Scope
from app.modules.connections import repositories
from app.modules.connections.models import Connection
from app.modules.connections.schemas import ConnectionCreate, ConnectionRead, ConnectionUpdate


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
) -> Page[ConnectionRead]:
    items, total = await repositories.list_connections(
        session, scope, page, area_id=area_id, status=status, package_id=package_id, q=q, sort=sort
    )
    return Page[ConnectionRead](
        items=[ConnectionRead.model_validate(c) for c in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


async def get_connection(
    session: AsyncSession, scope: Scope, connection_id: uuid.UUID
) -> Connection:
    connection = await repositories.get_connection(session, scope, connection_id)
    if connection is None:
        raise NotFoundError("Connection not found.")
    return connection


async def _check_area_and_package(
    session: AsyncSession, scope: Scope, area_id: int | None, package_id: int | None
) -> None:
    if area_id is not None and not await repositories.area_exists(session, scope, area_id):
        raise NotFoundError("Area not found.")
    if package_id is not None and not await repositories.package_exists(session, scope, package_id):
        raise NotFoundError("Package not found.")


async def create_connection(
    session: AsyncSession, scope: Scope, data: ConnectionCreate
) -> Connection:
    if await repositories.code_taken(session, scope, data.customer_code):
        raise ConflictError("A connection with this customer code already exists.")
    await _check_area_and_package(session, scope, data.area_id, data.package_id)
    connection = Connection(**data.model_dump())
    session.add(connection)
    await session.commit()
    return connection


async def update_connection(
    session: AsyncSession, scope: Scope, connection_id: uuid.UUID, data: ConnectionUpdate
) -> Connection:
    connection = await get_connection(session, scope, connection_id)
    # exclude_none: every column is NOT NULL, so an explicit null means "no change".
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    await _check_area_and_package(session, scope, changes.get("area_id"), changes.get("package_id"))
    for field, value in changes.items():
        setattr(connection, field, value)
    await session.commit()
    return connection


async def delete_connection(session: AsyncSession, scope: Scope, connection_id: uuid.UUID) -> None:
    connection = await get_connection(session, scope, connection_id)
    if await repositories.has_history(session, scope, connection_id):
        raise ConflictError(
            "This connection has bills or complaints. Set its status to disconnected instead."
        )
    await session.delete(connection)
    await session.commit()
