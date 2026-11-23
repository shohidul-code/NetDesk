"""HTTP only: parse input, check the role, call the service, shape the response."""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.auth.dependencies import CurrentScope, require_roles
from app.modules.packages import services
from app.modules.packages.models import Package
from app.modules.packages.schemas import PackageCreate, PackageRead, PackageUpdate

router = APIRouter(prefix="/packages", tags=["packages"])

Session = Annotated[AsyncSession, Depends(get_session)]
AdminOnly = [Depends(require_roles("admin"))]


@router.get("", response_model=list[PackageRead])
async def list_packages(
    session: Session, scope: CurrentScope, active: bool | None = None
) -> Sequence[Package]:
    return await services.list_packages(session, scope, active)


@router.post(
    "", response_model=PackageRead, status_code=status.HTTP_201_CREATED, dependencies=AdminOnly
)
async def create_package(session: Session, scope: CurrentScope, body: PackageCreate) -> Package:
    return await services.create_package(session, scope, body)


@router.patch("/{package_id}", response_model=PackageRead, dependencies=AdminOnly)
async def update_package(
    session: Session, scope: CurrentScope, package_id: int, body: PackageUpdate
) -> Package:
    return await services.update_package(session, scope, package_id, body)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=AdminOnly)
async def delete_package(session: Session, scope: CurrentScope, package_id: int) -> Response:
    await services.delete_package(session, scope, package_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
