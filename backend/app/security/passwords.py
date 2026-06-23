"""Password hashing (argon2 via passlib) — technical-spec §7."""
from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plaintext: str) -> str:
    return _pwd_context.hash(plaintext)


def verify_password(plaintext: str, password_hash: str) -> bool:
    return _pwd_context.verify(plaintext, password_hash)
