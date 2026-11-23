"""Access-control sweep (PROPOSAL §7.3, §13.1; Gate 1). Every request carries a real JWT:
no get_current_user override. Roles are checked before validation, and a customer can
never learn that another customer's rows exist (IDOR -> 404, same body as a missing id)."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute, iter_route_contexts
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.main import create_app
from app.modules.auth.dependencies import get_current_user
from app.modules.users.models import User
from tests.factories import (
    make_area,
    make_bill,
    make_complaint,
    make_connection,
    make_notice,
    make_user,
)

API = "/api/v1"
PUBLIC_PATHS = {f"{API}/health", f"{API}/auth/login", f"{API}/auth/register"}
WRITE_METHODS = {"POST", "PATCH", "DELETE"}


def _routes() -> list[tuple[str, str, str]]:
    """(METHOD, template, concrete path) for every API route, path params filled in."""
    found = []
    for ctx in iter_route_contexts(create_app().routes):
        route = ctx.route
        if not isinstance(route, APIRoute):
            continue
        concrete = ctx.path
        for param in route.dependant.path_params:
            value = 999999 if param.field_info.annotation is int else uuid.uuid4()
            concrete = concrete.replace("{" + param.name + "}", str(value))
        found.extend((m, ctx.path, concrete) for m in sorted(route.methods))
    return found


ROUTES = _routes()
# Customers may create complaints; login/register are public.
CUSTOMER_WRITES = [
    r
    for r in ROUTES
    if r[0] in WRITE_METHODS
    and r[1] not in PUBLIC_PATHS
    and (r[0], r[1]) != ("POST", f"{API}/complaints")
]
TECHNICIAN_WRITES = [
    r for r in CUSTOMER_WRITES if (r[0], r[1]) != ("PATCH", f"{API}/complaints/{{complaint_id}}")
]
NON_PUBLIC = [r for r in ROUTES if r[1] not in PUBLIC_PATHS]


def _ids(routes: list[tuple[str, str, str]]) -> list[str]:
    return [f"{m} {template}" for m, template, _ in routes]


@pytest.fixture
async def real_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides.pop(get_current_user, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _auth(user: User) -> dict[str, str]:
    exp = datetime.now(UTC) + timedelta(minutes=30)
    secret = get_settings().jwt_secret_key.get_secret_value()
    token = jwt.encode({"sub": str(user.id), "exp": exp}, secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_sweep_covers_the_write_routes() -> None:
    """Guard against a vacuous pass: the parametrized lists must not be empty."""
    covered = {t for _, t, _ in CUSTOMER_WRITES}
    assert {f"{API}/connections", f"{API}/packages"} <= covered
    assert TECHNICIAN_WRITES and NON_PUBLIC


@pytest.mark.parametrize("route", CUSTOMER_WRITES, ids=_ids(CUSTOMER_WRITES))
async def test_every_write_route_rejects_customer(
    route: tuple[str, str, str], real_client: AsyncClient, db_session: AsyncSession
) -> None:
    method, _, path = route
    customer = await make_user(db_session, "customer")

    response = await real_client.request(method, path, json={}, headers=_auth(customer))

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("route", TECHNICIAN_WRITES, ids=_ids(TECHNICIAN_WRITES))
async def test_admin_only_writes_reject_technician(
    route: tuple[str, str, str], real_client: AsyncClient, db_session: AsyncSession
) -> None:
    method, _, path = route
    technician = await make_user(db_session, "technician")

    response = await real_client.request(method, path, json={}, headers=_auth(technician))

    assert response.status_code == 403, response.text


@pytest.mark.parametrize("route", NON_PUBLIC, ids=_ids(NON_PUBLIC))
async def test_no_token_is_401_with_bearer_challenge(
    route: tuple[str, str, str], real_client: AsyncClient
) -> None:
    method, _, path = route

    response = await real_client.request(method, path, json={} if method != "GET" else None)

    assert response.status_code == 401, response.text
    assert response.headers["www-authenticate"] == "Bearer"


# --- IDOR (PROPOSAL §13.1) ------------------------------------------------------------


class World:
    """Customer A and customer B, each with a connection in a different area."""

    a: User
    b: User
    a_conn: Any
    b_conn: Any
    b_bill: Any
    b_complaint: Any
    a_notice: Any
    b_notice: Any


@pytest.fixture
async def world(db_session: AsyncSession, admin: User) -> World:
    w = World()
    w.a = await make_user(db_session, "customer")
    w.b = await make_user(db_session, "customer")
    area_a, area_b = await make_area(db_session), await make_area(db_session)
    w.a_conn = await make_connection(db_session, area_id=area_a.id, customer_user_id=w.a.id)
    w.b_conn = await make_connection(db_session, area_id=area_b.id, customer_user_id=w.b.id)
    w.b_bill = await make_bill(db_session, w.b_conn.id)
    w.b_complaint = await make_complaint(db_session, w.b_conn.id, w.b.id)
    w.a_notice = await make_notice(db_session, area_a.id, admin.id)
    w.b_notice = await make_notice(db_session, area_b.id, admin.id)
    return w


async def test_other_customers_connection_is_404(real_client: AsyncClient, world: World) -> None:
    response = await real_client.get(f"{API}/connections/{world.b_conn.id}", headers=_auth(world.a))

    assert response.status_code == 404


async def test_other_customers_bill_is_404(real_client: AsyncClient, world: World) -> None:
    """B's bill is not in A's list, and asking for it by connection finds nothing."""
    listing = await real_client.get(f"{API}/bills", headers=_auth(world.a))
    filtered = await real_client.get(
        f"{API}/bills", params={"connection_id": str(world.b_conn.id)}, headers=_auth(world.a)
    )

    assert listing.status_code == 200
    assert str(world.b_bill.id) not in {item["id"] for item in listing.json()["items"]}
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 0


async def test_customer_cannot_complain_about_other_customers_connection(
    real_client: AsyncClient, world: World
) -> None:
    response = await real_client.post(
        f"{API}/complaints",
        json={
            "connection_id": str(world.b_conn.id),
            "category": "no_internet",
            "description": "Not my line.",
        },
        headers=_auth(world.a),
    )

    assert response.status_code == 404


async def test_complaint_list_excludes_other_customers(
    real_client: AsyncClient, world: World
) -> None:
    response = await real_client.get(f"{API}/complaints", headers=_auth(world.a))

    assert response.status_code == 200
    assert str(world.b_complaint.id) not in {i["id"] for i in response.json()["items"]}


async def test_notice_list_excludes_other_areas(real_client: AsyncClient, world: World) -> None:
    response = await real_client.get(f"{API}/notices", headers=_auth(world.a))

    ids = {n["id"] for n in response.json()}
    assert response.status_code == 200
    assert str(world.a_notice.id) in ids  # not vacuous: A does see their own area's notice
    assert str(world.b_notice.id) not in ids


async def test_idor_404_body_matches_a_missing_id(real_client: AsyncClient, world: World) -> None:
    """No existence leak: another customer's connection looks exactly like a missing one."""
    other = await real_client.get(f"{API}/connections/{world.b_conn.id}", headers=_auth(world.a))
    missing = await real_client.get(f"{API}/connections/{uuid.uuid4()}", headers=_auth(world.a))

    def body(response: Any) -> dict[str, Any]:
        error = response.json()["error"]
        return {k: v for k, v in error.items() if k != "request_id"}

    assert other.status_code == missing.status_code == 404
    assert body(other) == body(missing)
