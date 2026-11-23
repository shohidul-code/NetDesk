"""Seed synthetic demo data (PROPOSAL §7.5). Safe to run any number of times.

    docker compose exec api python -m scripts.seed

Every row is upserted by a natural key (area code, package name, email, customer
code, connection + period, complaint/notice text), so a second run adds nothing.
A fixed random seed gives the same data every run. All names and numbers are
invented: phones sit in +88019000xxxxx, which no real subscriber uses here.
"""

import asyncio
import random
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.core.security import hash_password
from app.modules.areas.models import Area
from app.modules.billing.models import Bill
from app.modules.billing.services import due_date_for
from app.modules.complaints.models import Complaint
from app.modules.connections.models import Connection
from app.modules.notices.models import AreaNotice
from app.modules.packages.models import Package
from app.modules.users.models import Role, User

AREAS = [
    ("MIRPUR-10", "Mirpur 10", "মিরপুর ১০"),
    ("UTTARA-7", "Uttara Sector 7", "উত্তরা সেক্টর ৭"),
    ("MOHAMMADPUR", "Mohammadpur", "মোহাম্মদপুর"),
]
PACKAGES = [
    ("Basic 10", 10, "500.00"),
    ("Home 20", 20, "800.00"),
    ("Family 40", 40, "1200.00"),
    ("Pro 60", 60, "1500.00"),
]
USERS = [
    ("admin@netdesk.demo", "Demo Admin", "admin"),
    ("tech1@netdesk.demo", "Demo Technician One", "technician"),
    ("tech2@netdesk.demo", "Demo Technician Two", "technician"),
    ("customer1@netdesk.demo", "Demo Customer One", "customer"),
    ("customer2@netdesk.demo", "Demo Customer Two", "customer"),
    ("customer3@netdesk.demo", "Demo Customer Three", "customer"),
]
FIRST_NAMES = ["Rafiq", "Nasrin", "Tanvir", "Shirin", "Arif", "Mitu", "Sohel", "Lipi", "Jamil"]
LAST_NAMES = ["Hossain", "Akter", "Rahman", "Begum", "Karim", "Sultana", "Ahmed", "Khatun"]
# Fixed months, not "the last six", so every run produces the same bills.
PERIODS = ["2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"]
COMPLAINT_TEXT = {
    "no_internet": "Internet has been down since this morning.",
    "slow_speed": "Speed drops badly every evening.",
    "billing": "My bill looks higher than my package price.",
    "other": "Router light keeps blinking red.",
}


async def _count(session: AsyncSession, model: type) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def _upsert_lookups(session: AsyncSession, password: str) -> None:
    """Areas, packages and demo users; existing rows (same natural key) are left alone."""
    await session.execute(
        insert(Area)
        .values([{"code": c, "name": n, "name_bn": bn} for c, n, bn in AREAS])
        .on_conflict_do_nothing(index_elements=["code"])
    )
    await session.execute(
        insert(Package)
        .values(
            [{"name": n, "speed_mbps": s, "monthly_price_bdt": Decimal(p)} for n, s, p in PACKAGES]
        )
        .on_conflict_do_nothing(index_elements=["name"])
    )
    role_ids = dict((await session.execute(select(Role.name, Role.id))).all())
    pw_hash = hash_password(password)
    await session.execute(
        insert(User)
        .values(
            [
                {"email": e, "full_name": n, "password_hash": pw_hash, "role_id": role_ids[r]}
                for e, n, r in USERS
            ]
        )
        .on_conflict_do_nothing(index_elements=["email"])
    )


async def seed(session: AsyncSession) -> dict[str, int]:
    password = get_settings().seed_demo_password
    if password is None:
        raise SystemExit("Set SEED_DEMO_PASSWORD in .env before seeding demo accounts.")
    rng = random.Random(42)
    await _upsert_lookups(session, password.get_secret_value())

    area_ids = dict((await session.execute(select(Area.code, Area.id))).all())
    package_ids = dict((await session.execute(select(Package.name, Package.id))).all())
    users = dict((await session.execute(select(User.email, User.id))).all())
    admin_id = users["admin@netdesk.demo"]

    connections = [
        {
            "customer_code": f"ND-{n:06d}",
            "customer_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            "phone": f"+88019000{n:05d}",
            "address": f"House {rng.randint(1, 99)}, Road {rng.randint(1, 20)}",
            "area_id": area_ids[AREAS[(n - 1) % len(AREAS)][0]],
            "package_id": package_ids[rng.choice(PACKAGES)[0]],
            # The three demo customers own the first three connections.
            "customer_user_id": users.get(f"customer{n}@netdesk.demo"),
            "status": "disconnected" if n == 30 else "active",
        }
        for n in range(1, 31)
    ]
    await session.execute(
        insert(Connection)
        .values(connections)
        .on_conflict_do_nothing(index_elements=["customer_code"])
    )

    rows = (
        await session.execute(
            select(Connection.id, Connection.customer_code, Package.monthly_price_bdt)
            .join(Package, Package.id == Connection.package_id)
            .where(Connection.customer_code.like("ND-0000%"))
            .order_by(Connection.customer_code)
        )
    ).all()
    now = datetime.now(UTC)
    bills = []
    for connection_id, code, price in rows:
        for index, period in enumerate(PERIODS):
            # Older months are mostly paid; the latest month is mostly unpaid.
            paid = rng.random() < (0.9 if index < len(PERIODS) - 1 else 0.3)
            bills.append(
                {
                    "connection_id": connection_id,
                    "period": period,
                    "amount_bdt": price,
                    "due_date": due_date_for(period),
                    "status": "paid" if paid else "unpaid",
                    "paid_at": now if paid else None,
                    "payment_method": rng.choice(["bkash", "nagad", "cash"]) if paid else None,
                    "trx_id": f"SEED{code[3:]}{period.replace('-', '')}" if paid else None,
                    "verified_by": admin_id if paid else None,
                }
            )
    await session.execute(
        insert(Bill)
        .values(bills)
        .on_conflict_do_nothing(index_elements=["connection_id", "period"])
    )

    await _add_complaints(session, rows, users)
    await _add_notices(session, area_ids, admin_id, now)
    await session.commit()
    models = {
        "areas": Area,
        "packages": Package,
        "users": User,
        "connections": Connection,
        "bills": Bill,
        "complaints": Complaint,
        "notices": AreaNotice,
    }
    return {name: await _count(session, model) for name, model in models.items()}


async def _add_complaints(
    session: AsyncSession, rows: Sequence[Any], users: dict[str, uuid.UUID]
) -> None:
    """Ten complaints; the description is the natural key (no unique column exists)."""
    statuses = ["open", "open", "in_progress", "resolved", "closed"]
    for i in range(10):
        category = list(COMPLAINT_TEXT)[i % len(COMPLAINT_TEXT)]
        description = f"{COMPLAINT_TEXT[category]} (demo #{i + 1})"
        found = await session.execute(
            select(Complaint.id).where(Complaint.description == description)
        )
        if found.first() is None:
            session.add(
                Complaint(
                    connection_id=rows[i * 2][0],
                    created_by=users["admin@netdesk.demo"],
                    assigned_to=users["tech1@netdesk.demo"] if i % 2 else None,
                    category=category,
                    status=statuses[i % len(statuses)],
                    description=description,
                )
            )


async def _add_notices(
    session: AsyncSession, area_ids: dict[str, int], admin_id: uuid.UUID, now: datetime
) -> None:
    """One notice active now (relative to the run) and one that already ended."""
    notices = [
        (
            "MIRPUR-10",
            "outage",
            "ফাইবার কাটা পড়েছে, মেরামত চলছে।",
            "Fibre cut; repair under way.",
            now - timedelta(hours=2),
            now + timedelta(hours=6),
        ),
        (
            "UTTARA-7",
            "maintenance",
            "রাউটার আপগ্রেডের কাজ শেষ।",
            "Router upgrade finished.",
            datetime(2026, 10, 1, 18, tzinfo=UTC),
            datetime(2026, 10, 1, 22, tzinfo=UTC),
        ),
    ]
    for code, kind, message_bn, message_en, starts_at, ends_at in notices:
        found = await session.execute(
            select(AreaNotice.id).where(AreaNotice.message_en == message_en)
        )
        if found.first() is None:
            session.add(
                AreaNotice(
                    area_id=area_ids[code],
                    created_by=admin_id,
                    kind=kind,
                    message_bn=message_bn,
                    message_en=message_en,
                    starts_at=starts_at,
                    ends_at=ends_at,
                )
            )


async def main() -> None:
    async with get_sessionmaker()() as session:
        counts = await seed(session)
    print("Seeded:", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    asyncio.run(main())
