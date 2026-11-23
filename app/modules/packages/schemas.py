from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# Taka with two decimals, up to numeric(10,2).
Money = Decimal


class PackageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # blocks mass assignment

    name: str = Field(min_length=2, max_length=80)
    speed_mbps: int = Field(gt=0)
    monthly_price_bdt: Money = Field(ge=0, max_digits=10, decimal_places=2)
    is_active: bool = True


class PackageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=2, max_length=80)
    speed_mbps: int | None = Field(None, gt=0)
    monthly_price_bdt: Money | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    is_active: bool | None = None


class PackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    speed_mbps: int
    monthly_price_bdt: Money
    is_active: bool
