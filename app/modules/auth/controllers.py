from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.rate_limit import LOGIN_LIMIT, REGISTER_LIMIT, limiter
from app.modules.auth import services
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schemas import RegisterRequest, Token, UserRead
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(REGISTER_LIMIT)
async def register(request: Request, session: Session, body: RegisterRequest) -> User:
    """Public. `request` is required by slowapi, which reads the client IP from it."""
    return await services.claim_account(session, body)


@router.post("/login", response_model=Token)
@limiter.limit(LOGIN_LIMIT)
async def login(
    request: Request, session: Session, form: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """OAuth2 password form, so Swagger's Authorize button works. `username` is the email."""
    return await services.login(session, form.username, form.password)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user
