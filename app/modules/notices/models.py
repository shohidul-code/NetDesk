import uuid
from datetime import datetime
from typing import Literal, get_args

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.connections.models import _in_list

NoticeKind = Literal["outage", "maintenance"]


class AreaNotice(Base):
    """An outage or maintenance notice for one area (PROPOSAL §7.2)."""

    __tablename__ = "area_notices"
    __table_args__ = (
        CheckConstraint(_in_list("kind", get_args(NoticeKind)), name="kind_valid"),
        CheckConstraint("ends_at > starts_at", name="ends_after_start"),
        Index("ix_area_notices_area_id_starts_at", "area_id", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id", ondelete="RESTRICT"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(12))
    message_bn: Mapped[str] = mapped_column(String(500))
    message_en: Mapped[str] = mapped_column(String(500))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
