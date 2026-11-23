from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# A simple shape check, not full RFC validation: no new dependency. Lower-cased because
# the database stores emails in lower case (CHECK email = lower(email)).
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]
Password = Annotated[str, Field(min_length=10, max_length=128)]


class UserCreate(BaseModel):
    """Admin creates a technician. There is no role field, so a role can never be sent."""

    model_config = ConfigDict(extra="forbid")

    email: Email
    full_name: str = Field(min_length=2, max_length=120)
    password: Password


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(None, min_length=2, max_length=120)
    is_active: bool | None = None
