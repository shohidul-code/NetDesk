import uuid
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.modules.notices.models import NoticeKind


class NoticeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area_id: int
    kind: NoticeKind
    message_bn: str = Field(min_length=1, max_length=500)
    message_en: str = Field(min_length=1, max_length=500)
    # AwareDatetime rejects a time without a UTC offset, so every stored time is unambiguous.
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def _ends_after_start(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class NoticeUpdate(BaseModel):
    """Every field is optional. The start/end rule is checked in the service, because a
    PATCH may send only one of the two times."""

    model_config = ConfigDict(extra="forbid")

    area_id: int | None = None
    kind: NoticeKind | None = None
    message_bn: str | None = Field(None, min_length=1, max_length=500)
    message_en: str | None = Field(None, min_length=1, max_length=500)
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None


class NoticeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    area_id: int
    kind: NoticeKind
    message_bn: str
    message_en: str
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    created_by: uuid.UUID
