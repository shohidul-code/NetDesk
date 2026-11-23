"""Password hashing with Argon2id at the OWASP minimum (PROPOSAL §10.2, CLAUDE.md):
memory 19456 KiB, time cost 2, parallelism 1. JWT handling arrives in Phase 3."""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_password_hash = PasswordHash((Argon2Hasher(memory_cost=19456, time_cost=2, parallelism=1),))


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)
