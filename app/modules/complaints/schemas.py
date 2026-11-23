import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.complaints.models import ComplaintCategory, ComplaintStatus


class ComplaintCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # blocks mass assignment

    connection_id: uuid.UUID
    category: ComplaintCategory
    description: str = Field(min_length=1, max_length=1000)


class ComplaintUpdate(BaseModel):
    """`assigned_to: null` un-assigns, so None is meaningful there (not for status)."""

    model_config = ConfigDict(extra="forbid")

    status: ComplaintStatus | None = None
    assigned_to: uuid.UUID | None = None


class ComplaintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connection_id: uuid.UUID
    created_by: uuid.UUID
    assigned_to: uuid.UUID | None
    category: str
    status: str
    description: str
    created_at: datetime
    updated_at: datetime
