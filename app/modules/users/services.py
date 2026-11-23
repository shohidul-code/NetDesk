"""Business rules for staff accounts. Services own the transaction and call commit."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.pagination import Page, PageParams
from app.core.security import hash_password
from app.modules.auth.dependencies import Scope
from app.modules.auth.schemas import UserRead
from app.modules.users import repositories
from app.modules.users.models import RoleName, User
from app.modules.users.schemas import UserCreate, UserUpdate


async def create_technician(session: AsyncSession, scope: Scope, data: UserCreate) -> User:
    if await repositories.get_user_by_email(session, data.email) is not None:
        raise ConflictError("This email is already registered.")
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=await repositories.get_role(session, "technician"),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:  # two requests raced for the same new email
        await session.rollback()
        raise ConflictError("This email is already registered.") from exc
    return user


async def list_users(
    session: AsyncSession, scope: Scope, page: PageParams, role: RoleName | None
) -> Page[UserRead]:
    items, total = await repositories.list_users(session, scope, page, role)
    return Page[UserRead](
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


async def update_user(
    session: AsyncSession, scope: Scope, user_id: uuid.UUID, data: UserUpdate
) -> User:
    user = await repositories.get_user(session, scope, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    # `null` means "leave it"; both columns are NOT NULL.
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if (
        changes.get("is_active") is False
        and user.is_active
        and user.role.name == "admin"
        and await repositories.count_active_admins(session, scope) <= 1
    ):
        raise ConflictError("Cannot deactivate the last active admin.")
    for field, value in changes.items():
        setattr(user, field, value)
    await session.commit()
    return user
