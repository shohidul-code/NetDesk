"""Login. Every failure gives the same message, so the response never reveals whether
an email is registered (PROPOSAL §10.2)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.errors import UnauthorizedError
from app.modules.auth.schemas import Token
from app.modules.users import repositories as users

LOGIN_FAILED = "Incorrect email or password."


async def login(session: AsyncSession, email: str, password: str) -> Token:
    user = await users.get_user_by_email(session, email)
    if user is None:
        security.verify_password(password, security.DUMMY_HASH)  # same cost as a real check
        raise UnauthorizedError(LOGIN_FAILED)
    if not security.verify_password(password, user.password_hash) or not user.is_active:
        raise UnauthorizedError(LOGIN_FAILED)
    token, expires_in = security.create_access_token(user.id)
    return Token(access_token=token, expires_in=expires_in)
