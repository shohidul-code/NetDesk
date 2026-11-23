"""Small helpers that insert synthetic rows for tests. No real names or numbers.

Each helper adds the row, flushes (so it gets its id) and returns it. The test's
transaction is rolled back afterwards, so nothing is kept.
"""

import itertools
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.areas.models import Area
from app.modules.billing.models import Bill
from app.modules.complaints.models import Complaint
from app.modules.connections.models import Connection
from app.modules.notices.models import AreaNotice
from app.modules.packages.models import Package
from app.modules.users.models import Role, User

_counter = itertools.count(1)


def _n() -> int:
    return next(_counter)


async def make_user(session: AsyncSession, role: str = "admin", **kw: object) -> User:
    role_id = (await session.execute(select(Role.id).where(Role.name == role))).scalar_one()
    n = _n()
    user = User(
        email=f"{role}{n}@example.test",
        full_name=f"Test {role.title()} {n}",
        password_hash="not-a-real-hash",
        role_id=role_id,
        **kw,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user, ["role"])
    return user


async def make_area(session: AsyncSession, **kw: object) -> Area:
    n = _n()
    area = Area(**{"code": f"AREA-{n}", "name": f"Area {n}", "name_bn": f"এলাকা {n}", **kw})
    session.add(area)
    await session.flush()
    return area


async def make_package(session: AsyncSession, **kw: object) -> Package:
    n = _n()
    fields = {"name": f"Plan {n}", "speed_mbps": 20, "monthly_price_bdt": Decimal("1000.00")}
    package = Package(**{**fields, **kw})
    session.add(package)
    await session.flush()
    return package


async def make_connection(session: AsyncSession, **kw: object) -> Connection:
    n = _n()
    if "area_id" not in kw:
        kw["area_id"] = (await make_area(session)).id
    if "package_id" not in kw:
        kw["package_id"] = (await make_package(session)).id
    fields = {
        "customer_code": f"ND-{n:06d}",
        "customer_name": f"Test Customer {n}",
        "phone": f"+88019{n:08d}",
        "address": f"House {n}, Test Road",
    }
    connection = Connection(**{**fields, **kw})
    session.add(connection)
    await session.flush()
    return connection


async def make_bill(session: AsyncSession, connection_id: uuid.UUID, **kw: object) -> Bill:
    fields = {
        "connection_id": connection_id,
        "period": "2026-11",
        "amount_bdt": Decimal("1000.00"),
        "due_date": date(2026, 12, 10),
    }
    bill = Bill(**{**fields, **kw})
    session.add(bill)
    await session.flush()
    return bill


async def make_complaint(
    session: AsyncSession, connection_id: uuid.UUID, created_by: uuid.UUID, **kw: object
) -> Complaint:
    fields = {
        "connection_id": connection_id,
        "created_by": created_by,
        "category": "no_internet",
        "description": "Internet is down since morning.",
    }
    complaint = Complaint(**{**fields, **kw})
    session.add(complaint)
    await session.flush()
    return complaint


async def make_notice(
    session: AsyncSession, area_id: int, created_by: uuid.UUID, **kw: object
) -> AreaNotice:
    now = datetime.now(UTC)
    fields = {
        "area_id": area_id,
        "created_by": created_by,
        "kind": "outage",
        "message_bn": "ফাইবার কাটা পড়েছে।",
        "message_en": "Fibre cut in the area.",
        "starts_at": now - timedelta(hours=1),
        "ends_at": now + timedelta(hours=3),
    }
    notice = AreaNotice(**{**fields, **kw})
    session.add(notice)
    await session.flush()
    return notice
