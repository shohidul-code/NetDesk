"""HTTP only: parse input, check the role, call the service, shape the response."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import Page, PageQuery
from app.modules.auth.dependencies import CurrentScope, require_roles
from app.modules.auth.schemas import UserRead
from app.modules.users import services
from app.modules.users.models import RoleName, User
from app.modules.users.schemas import UserCreate, UserUpdate

# Every route here is admin-only.
router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_roles("admin"))])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_technician(session: Session, scope: CurrentScope, body: UserCreate) -> User:
    return await services.create_technician(session, scope, body)


@router.get("", response_model=Page[UserRead])
async def list_users(
    session: Session, scope: CurrentScope, page: PageQuery, role: RoleName | None = None
) -> Page[UserRead]:
    return await services.list_users(session, scope, page, role)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    session: Session, scope: CurrentScope, user_id: uuid.UUID, body: UserUpdate
) -> User:
    return await services.update_user(session, scope, user_id, body)
