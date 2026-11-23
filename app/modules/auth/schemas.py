import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRead(BaseModel):
    """A user as the API shows it. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool

    @field_validator("role", mode="before")
    @classmethod
    def _role_name(cls, value: Any) -> Any:
        # The ORM gives a Role object; the API shows just its name.
        return getattr(value, "name", value)
