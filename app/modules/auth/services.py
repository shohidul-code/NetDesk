"""Login. Every failure gives the same message, so the response never reveals whether
an email is registered (PROPOSAL §10.2)."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError
from app.modules.auth.schemas import RegisterRequest, Token
from app.modules.users import repositories as users
from app.modules.users.models import User

LOGIN_FAILED = "Incorrect email or password."
EMAIL_TAKEN = "This email is already registered."


async def login(session: AsyncSession, email: str, password: str) -> Token:
    user = await users.get_user_by_email(session, email)
    if user is None:
        security.verify_password(password, security.DUMMY_HASH)  # same cost as a real check
        raise UnauthorizedError(LOGIN_FAILED)
    if not security.verify_password(password, user.password_hash) or not user.is_active:
        raise UnauthorizedError(LOGIN_FAILED)
    token, expires_in = security.create_access_token(user.id)
    return Token(access_token=token, expires_in=expires_in)


async def claim_account(session: AsyncSession, data: RegisterRequest) -> User:
    """Create a customer account and link it to the connection the ISP already made."""
    connection = await users.find_connection_to_claim(session, data.customer_code, data.phone)
    if connection is None:
        raise NotFoundError("No connection matches this customer code and phone.")
    if connection.customer_user_id is not None:
        raise ConflictError("This connection is already claimed.")
    if await users.get_user_by_email(session, data.email) is not None:
        raise ConflictError(EMAIL_TAKEN)
    user = User(
        email=data.email,
        full_name=connection.customer_name,
        password_hash=security.hash_password(data.password),
        role=await users.get_role(session, "customer"),
    )
    session.add(user)
    await session.flush()  # gives the user its id
    connection.customer_user_id = user.id
    try:
        await session.commit()
    except IntegrityError as exc:  # two requests raced for the same new email
        await session.rollback()
        raise ConflictError(EMAIL_TAKEN) from exc
    return user
