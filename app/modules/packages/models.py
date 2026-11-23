from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Package(Base):
    """An internet plan. Lookup table: int id (PROPOSAL §7.2)."""

    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint("speed_mbps > 0", name="speed_positive"),
        CheckConstraint("monthly_price_bdt >= 0", name="price_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    speed_mbps: Mapped[int]
    # Money is numeric(10,2) taka, never float.
    monthly_price_bdt: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
