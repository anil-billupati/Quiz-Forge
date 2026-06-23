"""Password hashing (argon2 via passlib) — technical-spec §7."""
from __future__ import annotations

import secrets

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plaintext: str) -> str:
    return _pwd_context.hash(plaintext)


def verify_password(plaintext: str, password_hash: str) -> bool:
    return _pwd_context.verify(plaintext, password_hash)


def generate_one_time_password() -> str:
    """A URL-safe one-time password for bulk-imported participants (F5).

    Returned once to the importing Org Admin for out-of-band distribution; only
    its hash is stored. The participant changes it via /auth/change-password.
    """
    return secrets.token_urlsafe(9)  # ~12 chars, cryptographically strong
