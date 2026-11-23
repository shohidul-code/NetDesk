from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.auth import services
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schemas import Token, UserRead
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/login", response_model=Token)
async def login(session: Session, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """OAuth2 password form, so Swagger's Authorize button works. `username` is the email."""
    return await services.login(session, form.username, form.password)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user
