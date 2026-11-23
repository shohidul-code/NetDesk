"""Limit/offset pages with a total count (PROPOSAL §8.2)."""

from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class PageParams(BaseModel):
    limit: int
    offset: int


def _page_params(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


# Route parameter type: `page: PageQuery`. limit is 1-100 (default 20); offset >= 0.
PageQuery = Annotated[PageParams, Depends(_page_params)]
