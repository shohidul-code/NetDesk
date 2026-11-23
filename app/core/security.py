"""Passwords and access tokens (PROPOSAL §10.2, CLAUDE.md).

- Passwords: Argon2id at the OWASP minimum: memory 19456 KiB, time cost 2, parallelism 1.
- Tokens: JWT, HS256, 30-minute expiry. The token holds only `sub` (the user id) and
  `exp`; role and is_active are loaded from the database on every request, so a role
  change or deactivation takes effect at once.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings

ALGORITHM = "HS256"

_password_hash = PasswordHash((Argon2Hasher(memory_cost=19456, time_cost=2, parallelism=1),))

# Checked against when the email is unknown, so a failed login costs the same time
# whether or not the account exists (no user enumeration by timing).
DUMMY_HASH = _password_hash.hash("dummy-password-for-timing-only")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Return the token and its lifetime in seconds."""
    minutes = get_settings().access_token_expire_minutes
    expires = datetime.now(UTC) + timedelta(minutes=minutes)
    token = jwt.encode(
        {"sub": str(user_id), "exp": expires},
        get_settings().jwt_secret_key.get_secret_value(),
        algorithm=ALGORITHM,
    )
    return token, minutes * 60


def decode_access_token(token: str) -> uuid.UUID:
    """Return the user id. Raises jwt.InvalidTokenError (expired, forged, malformed)."""
    payload = jwt.decode(
        token,
        get_settings().jwt_secret_key.get_secret_value(),
        algorithms=[ALGORITHM],  # a fixed list blocks the "alg: none" trick
        options={"require": ["sub", "exp"]},
    )
    try:
        return uuid.UUID(payload["sub"])
    except ValueError as exc:
        raise jwt.InvalidTokenError("sub is not a user id") from exc
