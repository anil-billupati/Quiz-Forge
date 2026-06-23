"""JWT access tokens and opaque rotating refresh tokens (FR-4, BR-20).

Access tokens are short-lived JWTs carrying role + tenant scope. Refresh tokens
are opaque random strings; only their sha256 hash is persisted (RefreshToken),
and they rotate on every use within a token family for reuse detection.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()


class TokenError(Exception):
    """Raised when an access token is invalid or expired."""


def create_access_token(*, user_id: str, role: str, tenant_id: str | None) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "role": role,
        "tenant_id": tenant_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:  # expired, bad signature, malformed
        raise TokenError(str(exc)) from exc
    if claims.get("type") != "access":
        raise TokenError("Not an access token")
    return claims


def generate_refresh_token() -> str:
    """Return a new opaque refresh token (the plaintext sent to the client)."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage; never persist the plaintext."""
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=settings.refresh_token_ttl_seconds)
