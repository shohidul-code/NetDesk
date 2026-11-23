from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.areas.models import Area
from app.modules.auth.dependencies import Scope


async def list_areas(session: AsyncSession, scope: Scope) -> Sequence[Area]:
    # Every role may see every area, so the scope adds no filter here.
    return (await session.execute(select(Area).order_by(Area.code))).scalars().all()
