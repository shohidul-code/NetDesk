"""The seed is idempotent and synthetic (PROPOSAL §7.5). It runs inside the test's
rolled-back transaction, so the shared database is left untouched."""

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import verify_password
from app.modules.connections.models import Connection
from app.modules.users.models import User
from scripts.seed import seed

EXPECTED = {
    "areas": 3,
    "packages": 4,
    "users": 6,
    "connections": 30,
    "bills": 180,
    "complaints": 10,
    "notices": 2,
}


@pytest.fixture(autouse=True)
def _demo_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "seed_demo_password", SecretStr("demo-only-pass-123"))


async def test_seed_twice_gives_the_same_counts(db_session: AsyncSession) -> None:
    first = await seed(db_session)
    second = await seed(db_session)

    assert first == EXPECTED
    assert second == EXPECTED


async def test_demo_passwords_are_argon2_hashed(db_session: AsyncSession) -> None:
    await seed(db_session)
    admin = (
        await db_session.execute(select(User).where(User.email == "admin@netdesk.demo"))
    ).scalar_one()

    assert admin.password_hash.startswith("$argon2id$")
    assert "m=19456,t=2,p=1" in admin.password_hash
    assert verify_password("demo-only-pass-123", admin.password_hash)


async def test_seed_needs_a_demo_password(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "seed_demo_password", None)

    with pytest.raises(SystemExit, match="SEED_DEMO_PASSWORD"):
        await seed(db_session)


async def test_seeded_phones_are_in_the_fake_range(db_session: AsyncSession) -> None:
    """Synthetic data only: every number sits in +88019000xxxxx, not a real subscriber."""
    await seed(db_session)
    outside = await db_session.execute(
        select(func.count())
        .select_from(Connection)
        .where(Connection.customer_code.like("ND-0000%"))
        .where(~Connection.phone.like("+88019000%"))
    )

    assert outside.scalar() == 0
