"""Argument models for the agent tools, and the result `execute` hands back to the chat loop.

`extra="forbid"`: a model that invents an argument gets `invalid_arguments`, not silence.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

PERIOD = r"^\d{4}-(0[1-9]|1[0-2])$"


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GetMyBillStatusArgs(_Args):
    period: str | None = Field(default=None, pattern=PERIOD, description="Month as YYYY-MM.")


class GetMyAreaStatusArgs(_Args):
    pass


class LookupCustomerBillsArgs(_Args):
    customer_code: str = Field(pattern=r"^ND-\d{6}$", description="Customer code, e.g. ND-000123.")
    period: str | None = Field(default=None, pattern=PERIOD, description="Month as YYYY-MM.")


class GetAreaServiceStatusArgs(_Args):
    area_code: str = Field(min_length=1, max_length=20, description="Area code.")


@dataclass(frozen=True)
class ToolOutcome:
    name: str
    ok: bool
    content: str  # the JSON string sent back to the model
