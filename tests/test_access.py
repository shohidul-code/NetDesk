"""The stub current user, roles and Scope (Phase 2). Phase 3 replaces the stub with JWT."""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.modules.auth.dependencies import Scope, get_current_user, get_scope, require_roles
from app.modules.users.models import User
from tests.factories import make_user


async def test_stub_returns_an_active_admin(db_session: AsyncSession, admin: User) -> None:
    user = await get_current_user(db_session)

    assert user.role.name == "admin"


async def test_stub_without_admin_is_401(db_session: AsyncSession) -> None:
    with pytest.raises(UnauthorizedError):
        await get_current_user(db_session)


async def test_scope_holds_id_and_role(db_session: AsyncSession) -> None:
    customer = await make_user(db_session, "customer")

    scope = await get_scope(customer)

    assert scope == Scope(user_id=customer.id, role="customer")
    assert not scope.is_staff


async def test_require_roles_gives_403_to_other_roles(app: FastAPI, as_user: object) -> None:
    @app.get("/test/admin-only")
    async def admin_only(user: Annotated[User, Depends(require_roles("admin"))]) -> dict[str, str]:
        return {"role": user.role.name}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        allowed = await c.get("/test/admin-only")
        await as_user("customer")  # type: ignore[operator]
        denied = await c.get("/test/admin-only")

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"
