"""GET /knowledge/documents: staff see which help articles are indexed (PROPOSAL §8.1).
Customers never list documents; they only see public articles through chat citations."""

from collections.abc import Sequence
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.auth.dependencies import require_roles
from app.modules.knowledge import repositories
from app.modules.knowledge.models import KnowledgeDocument

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    language: str
    visibility: str
    status: str
    source_updated: date
    embedding_model: str


@router.get(
    "/documents",
    response_model=list[KnowledgeDocumentRead],
    dependencies=[Depends(require_roles("admin", "technician"))],
)
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Sequence[KnowledgeDocument]:
    return await repositories.list_documents(session)
