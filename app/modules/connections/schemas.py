import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.phone import BDPhone
from app.modules.connections.models import ConnectionStatus


class ConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # blocks mass assignment

    customer_code: str = Field(pattern=r"^ND-\d{6}$")
    customer_name: str = Field(min_length=2, max_length=120)
    phone: BDPhone
    address: str = Field(max_length=300)
    area_id: int
    package_id: int
    status: ConnectionStatus = "active"


class ConnectionUpdate(BaseModel):
    """No customer_code: it is immutable, and extra="forbid" turns it into a 422."""

    model_config = ConfigDict(extra="forbid")

    customer_name: str | None = Field(None, min_length=2, max_length=120)
    phone: BDPhone | None = None
    address: str | None = Field(None, max_length=300)
    area_id: int | None = None
    package_id: int | None = None
    status: ConnectionStatus | None = None


class ConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_code: str
    customer_name: str
    phone: str
    address: str
    status: str
    area_id: int
    package_id: int
    customer_user_id: uuid.UUID | None
    created_at: datetime
