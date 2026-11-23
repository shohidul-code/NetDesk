from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.areas import services
from app.modules.areas.models import Area
from app.modules.areas.schemas import AreaRead
from app.modules.auth.dependencies import CurrentScope

router = APIRouter(prefix="/areas", tags=["areas"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[AreaRead])
async def list_areas(session: Session, scope: CurrentScope) -> Sequence[Area]:
    return await services.list_areas(session, scope)
