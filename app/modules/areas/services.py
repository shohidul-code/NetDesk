from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.areas import repositories
from app.modules.areas.models import Area
from app.modules.auth.dependencies import Scope


async def list_areas(session: AsyncSession, scope: Scope) -> Sequence[Area]:
    return await repositories.list_areas(session, scope)
