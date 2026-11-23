import uuid
from datetime import datetime
from typing import Literal, get_args

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

ConnectionStatus = Literal["active", "suspended", "disconnected"]


def _in_list(column: str, values: tuple[str, ...]) -> str:
    """SQL for `column IN ('a', 'b')`, built from a Literal so code and DB agree."""
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Connection(Base):
    """One customer's internet connection: the main domain resource (PROPOSAL §7.2)."""

    __tablename__ = "connections"
    __table_args__ = (
        CheckConstraint(_in_list("status", get_args(ConnectionStatus)), name="status_valid"),
        Index("ix_connections_area_id_status", "area_id", "status"),
        Index("ix_connections_package_id", "package_id"),
        Index("ix_connections_phone", "phone"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    customer_code: Mapped[str] = mapped_column(String(9), unique=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    # Stored in E.164 form: +8801XXXXXXXXX.
    phone: Mapped[str] = mapped_column(String(14))
    address: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(
        String(12), default="active", server_default=text("'active'")
    )
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id", ondelete="RESTRICT"))
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id", ondelete="RESTRICT"))
    # Null until the customer claims the connection (Phase 3 register flow).
    customer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
