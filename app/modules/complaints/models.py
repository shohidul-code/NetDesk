import uuid
from datetime import datetime
from typing import Literal, get_args

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.connections.models import _in_list

ComplaintCategory = Literal["no_internet", "slow_speed", "billing", "other"]
ComplaintStatus = Literal["open", "in_progress", "resolved", "closed"]


class Complaint(Base):
    """A support ticket for one connection (PROPOSAL §7.2)."""

    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint(_in_list("category", get_args(ComplaintCategory)), name="category_valid"),
        CheckConstraint(_in_list("status", get_args(ComplaintStatus)), name="status_valid"),
        Index("ix_complaints_status_created_at", "status", "created_at"),
        Index("ix_complaints_connection_id", "connection_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connections.id", ondelete="RESTRICT")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    category: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(12), default="open", server_default=text("'open'"))
    description: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
