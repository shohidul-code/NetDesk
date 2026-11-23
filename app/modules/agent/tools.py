"""The four tool handlers: thin, read-only wrappers over two services (PROPOSAL §9.5).
No business rule lives here, so REST and MCP can call the same services."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent.schemas import (
    GetAreaServiceStatusArgs,
    GetMyAreaStatusArgs,
    GetMyBillStatusArgs,
    LookupCustomerBillsArgs,
)
from app.modules.auth.dependencies import Scope
from app.modules.billing import services as billing
from app.modules.notices import services as notices

GET_MY_BILL_STATUS_DESCRIPTION = (
    "Get the signed-in customer's own bills: package, connection status, the last six "
    "bills (period, amount in taka, paid or unpaid, due date) and the total still due. "
    "Pass period (YYYY-MM) to see one month only."
)
GET_MY_AREA_STATUS_DESCRIPTION = (
    "Get the service status of the signed-in customer's area: active outage or "
    "maintenance notices, how many complaints are open in the area, and the customer's "
    "own open complaints."
)
LOOKUP_CUSTOMER_BILLS_DESCRIPTION = (
    "Staff only. Look up one customer's bills by customer code (ND-000123): name, "
    "package, connection status, the last six bills and the total due. "
    "Pass period (YYYY-MM) to see one month only."
)
GET_AREA_SERVICE_STATUS_DESCRIPTION = (
    "Staff only. Get the service status of one area by area code: active notices, "
    "open complaints by category, and the age in hours of the oldest open complaint."
)


async def get_my_bill_status(
    session: AsyncSession, scope: Scope, args: GetMyBillStatusArgs
) -> dict[str, Any]:
    return await billing.bill_status(session, scope, period=args.period)


async def get_my_area_status(
    session: AsyncSession, scope: Scope, args: GetMyAreaStatusArgs
) -> dict[str, Any]:
    return await notices.area_status(session, scope)


async def lookup_customer_bills(
    session: AsyncSession, scope: Scope, args: LookupCustomerBillsArgs
) -> dict[str, Any]:
    return await billing.bill_status(
        session, scope, customer_code=args.customer_code, period=args.period
    )


async def get_area_service_status(
    session: AsyncSession, scope: Scope, args: GetAreaServiceStatusArgs
) -> dict[str, Any]:
    return await notices.area_status(session, scope, area_code=args.area_code)
