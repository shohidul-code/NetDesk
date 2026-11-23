"""Login, tokens and /auth/me (PROPOSAL §6.10, §10.2). No current-user shortcut here:
every request carries a real JWT."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import get_settings
from app.core.security import hash_password
from app.modules.auth.dependencies import get_current_user, require_roles
from app.modules.users.models import Role, User
from tests.factories import make_user

PASSWORD = "correct-horse-battery"


@pytest.fixture
async def real_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """The app with the test's session but WITHOUT the act-as-admin shortcut."""
    app.dependency_overrides.pop(get_current_user, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _user(db_session: AsyncSession, role: str = "customer", **kw: object) -> User:
    return await make_user(db_session, role, password_hash=hash_password(PASSWORD), **kw)


async def _login(client: AsyncClient, email: str, password: str = PASSWORD) -> tuple[int, Any]:
    response = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    return response.status_code, response.json()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(sub: str, *, minutes: int = 30, key: str | None = None) -> str:
    secret = key or get_settings().jwt_secret_key.get_secret_value()
    exp = datetime.now(UTC) + timedelta(minutes=minutes)
    return jwt.encode({"sub": sub, "exp": exp}, secret, algorithm="HS256")


async def test_login_returns_a_30_minute_bearer_token(
    real_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _user(db_session)

    status, body = await _login(real_client, user.email.upper())  # case-insensitive email

    assert status == 200
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800


async def test_token_holds_only_sub_and_exp(
    real_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Role and is_active are read from the database each request, never from the token."""
    user = await _user(db_session)
    _, body = await _login(real_client, user.email)

    payload = jwt.decode(
        body["access_token"], get_settings().jwt_secret_key.get_secret_value(), ["HS256"]
    )

    assert set(payload) == {"sub", "exp"}
    assert payload["sub"] == str(user.id)


async def test_unknown_email_and_wrong_password_get_identical_401(
    real_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _user(db_session)

    wrong_status, wrong_password = await _login(real_client, user.email, "not-the-password")
    unknown_status, unknown_email = await _login(real_client, "nobody@example.test")

    assert wrong_status == unknown_status == 401
    wrong_password["error"].pop("request_id")
    unknown_email["error"].pop("request_id")
    assert wrong_password == unknown_email


async def test_unknown_email_still_runs_a_hash_check(
    real_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the dummy check, an unknown email answers faster and leaks that it is unknown."""
    calls: list[str] = []
    real_verify = security.verify_password

    def counting_verify(password: str, password_hash: str) -> bool:
        calls.append(password_hash)
        return real_verify(password, password_hash)

    monkeypatch.setattr(security, "verify_password", counting_verify)

    await _login(real_client, "nobody@example.test")

    assert len(calls) == 1


async def test_inactive_user_cannot_log_in(
    real_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _user(db_session, is_active=False)

    status, _ = await _login(real_client, user.email)

    assert status == 401


async def test_me_returns_the_user(real_client: AsyncClient, db_session: AsyncSession) -> None:
    user = await _user(db_session)
    _, body = await _login(real_client, user.email)

    response = await real_client.get("/api/v1/auth/me", headers=_bearer(body["access_token"]))

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": "customer",
        "is_active": True,
    }


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-jwt"}, {"Authorization": "Basic dXNlcjpwYXNz"}],
)
async def test_me_without_a_valid_token_is_401(
    real_client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await real_client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_expired_token_is_401(real_client: AsyncClient, db_session: AsyncSession) -> None:
    user = await _user(db_session)
    expired = _token(str(user.id), minutes=-1)

    response = await real_client.get("/api/v1/auth/me", headers=_bearer(expired))

    assert response.status_code == 401


async def test_token_signed_with_another_key_is_401(
    real_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _user(db_session)
    forged = _token(str(user.id), key="an-attacker-key-that-is-long-enough-123456")

    response = await real_client.get("/api/v1/auth/me", headers=_bearer(forged))

    assert response.status_code == 401


async def test_token_for_unknown_user_is_401(real_client: AsyncClient) -> None:
    unknown = _token(str(uuid.uuid4()))

    response = await real_client.get("/api/v1/auth/me", headers=_bearer(unknown))

    assert response.status_code == 401


async def test_deactivated_user_token_stops_working(
    real_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _user(db_session)
    _, body = await _login(real_client, user.email)

    user.is_active = False
    await db_session.flush()
    response = await real_client.get("/api/v1/auth/me", headers=_bearer(body["access_token"]))

    assert response.status_code == 401


async def test_role_change_takes_effect_without_a_new_token(
    app: FastAPI, real_client: AsyncClient, db_session: AsyncSession
) -> None:
    @app.get("/test/admin-only")
    async def admin_only(user: Annotated[User, Depends(require_roles("admin"))]) -> dict[str, str]:
        return {"ok": "yes"}

    user = await _user(db_session, "technician")
    token = _token(str(user.id))
    before = await real_client.get("/test/admin-only", headers=_bearer(token))

    admin_role = await db_session.get(Role, 1)
    assert admin_role is not None and admin_role.name == "admin"
    user.role_id = admin_role.id
    await db_session.flush()
    db_session.expire(user, ["role"])
    after = await real_client.get("/test/admin-only", headers=_bearer(token))

    assert before.status_code == 403
    assert after.status_code == 200
