"""Tool registry: which tools each role is offered, and the only way to run one.

The model never decides access. `tools_for` shows a role its own tools; `execute` checks
the role again, because a model can invent a call to a tool it was never offered.
Every failure becomes a small JSON error the model can read; none echoes a value.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.agent import tools
from app.modules.agent.schemas import (
    GetAreaServiceStatusArgs,
    GetMyAreaStatusArgs,
    GetMyBillStatusArgs,
    LookupCustomerBillsArgs,
    ToolOutcome,
)
from app.modules.auth.dependencies import Scope
from app.modules.users.models import RoleName, User

logger = logging.getLogger(__name__)

TOOL_TIMEOUT_SECONDS = 5
MAX_RESULT_BYTES = 4096

Handler = Callable[[AsyncSession, Scope, Any], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel]
    roles: frozenset[RoleName]
    handler: Handler


_CUSTOMER: frozenset[RoleName] = frozenset({"customer"})
_STAFF: frozenset[RoleName] = frozenset({"technician", "admin"})

REGISTRY: dict[str, ToolDefinition] = {
    d.name: d
    for d in (
        ToolDefinition(
            "get_my_bill_status",
            tools.GET_MY_BILL_STATUS_DESCRIPTION,
            GetMyBillStatusArgs,
            _CUSTOMER,
            tools.get_my_bill_status,
        ),
        ToolDefinition(
            "get_my_area_status",
            tools.GET_MY_AREA_STATUS_DESCRIPTION,
            GetMyAreaStatusArgs,
            _CUSTOMER,
            tools.get_my_area_status,
        ),
        ToolDefinition(
            "lookup_customer_bills",
            tools.LOOKUP_CUSTOMER_BILLS_DESCRIPTION,
            LookupCustomerBillsArgs,
            _STAFF,
            tools.lookup_customer_bills,
        ),
        ToolDefinition(
            "get_area_service_status",
            tools.GET_AREA_SERVICE_STATUS_DESCRIPTION,
            GetAreaServiceStatusArgs,
            _STAFF,
            tools.get_area_service_status,
        ),
    )
}


def tools_for(role: RoleName) -> list[dict[str, Any]]:
    """OpenAI function-tool specs for the tools this role may use, and no others."""
    return [
        {
            "type": "function",
            "function": {
                "name": d.name,
                "description": d.description,
                "parameters": d.args_model.model_json_schema(),
            },
        }
        for d in REGISTRY.values()
        if role in d.roles
    ]


def _error(name: str, error: str, **extra: Any) -> ToolOutcome:
    return ToolOutcome(name, False, json.dumps({"error": error, **extra}))


async def execute(session: AsyncSession, user: User, name: str, arguments: str) -> ToolOutcome:
    """Run one tool call for `user`. Only unexpected bugs raise; everything else is a
    ToolOutcome the chat loop can send straight back to the model."""
    scope = Scope(user_id=user.id, role=user.role.name)  # type: ignore[arg-type]
    definition = REGISTRY.get(name)
    if definition is None or scope.role not in definition.roles:
        logger.warning("security: tool_not_available tool=%r user=%s", name[:64], user.id)
        return _error(name, "tool_not_available")
    try:
        args = definition.args_model.model_validate_json(arguments or "{}")
    except ValidationError as exc:
        # Field names only: the values may be anything the model (or a user) typed.
        fields = [".".join(map(str, e["loc"])) or "arguments" for e in exc.errors()]
        return _error(name, "invalid_arguments", fields=fields)
    try:
        result = await asyncio.wait_for(
            definition.handler(session, scope, args), timeout=TOOL_TIMEOUT_SECONDS
        )
    except TimeoutError:
        return _error(name, "timeout")
    except NotFoundError as exc:
        details = exc.details if isinstance(exc.details, dict) else {}
        return _error(name, details.get("code", "not_found"))
    content = json.dumps(result, ensure_ascii=False)
    if len(content.encode()) > MAX_RESULT_BYTES:
        return _error(name, "result_too_large")
    return ToolOutcome(name, True, content)
