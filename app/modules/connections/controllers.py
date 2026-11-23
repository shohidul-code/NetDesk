"""HTTP only: parse input, check the role, call the service, shape the response."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import Page, PageQuery
from app.modules.auth.dependencies import CurrentScope, require_roles
from app.modules.connections import services
from app.modules.connections.models import Connection, ConnectionStatus
from app.modules.connections.schemas import ConnectionCreate, ConnectionRead, ConnectionUpdate

router = APIRouter(prefix="/connections", tags=["connections"])

Session = Annotated[AsyncSession, Depends(get_session)]
AdminOnly = [Depends(require_roles("admin"))]

# Allowlist: anything else is a 422, so user input never reaches ORDER BY.
SortKey = Literal[
    "customer_code",
    "-customer_code",
    "customer_name",
    "-customer_name",
    "created_at",
    "-created_at",
]


@router.get("", response_model=Page[ConnectionRead])
async def list_connections(
    session: Session,
    scope: CurrentScope,
    page: PageQuery,
    area_id: int | None = None,
    status: ConnectionStatus | None = None,
    package_id: int | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    sort: SortKey = "customer_code",
) -> Page[ConnectionRead]:
    return await services.list_connections(
        session, scope, page, area_id=area_id, status=status, package_id=package_id, q=q, sort=sort
    )


@router.get("/{connection_id}", response_model=ConnectionRead)
async def get_connection(
    session: Session, scope: CurrentScope, connection_id: uuid.UUID
) -> Connection:
    return await services.get_connection(session, scope, connection_id)


@router.post(
    "", response_model=ConnectionRead, status_code=status.HTTP_201_CREATED, dependencies=AdminOnly
)
async def create_connection(
    session: Session, scope: CurrentScope, body: ConnectionCreate
) -> Connection:
    return await services.create_connection(session, scope, body)


@router.patch("/{connection_id}", response_model=ConnectionRead, dependencies=AdminOnly)
async def update_connection(
    session: Session, scope: CurrentScope, connection_id: uuid.UUID, body: ConnectionUpdate
) -> Connection:
    return await services.update_connection(session, scope, connection_id, body)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=AdminOnly)
async def delete_connection(
    session: Session, scope: CurrentScope, connection_id: uuid.UUID
) -> Response:
    await services.delete_connection(session, scope, connection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
