"""Authentication service: login, refresh rotation, logout, change password.

Refresh tokens rotate on every use (BR-20): the presented token is revoked and
a new one issued in the same family. Presenting an already-revoked token is
treated as reuse and revokes the whole family (defence against token theft).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.organization import Organization
from app.models.user import RefreshToken, User
from app.security.passwords import hash_password, verify_password
from app.security.tokens import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_expiry,
)

settings = get_settings()


async def _resolve_user(session: AsyncSession, email: str, tenant_slug: str | None) -> User | None:
    """Look up a user by email, scoped by tenant_slug for non-super-admins."""
    if tenant_slug:
        org = (
            await session.execute(select(Organization).where(Organization.slug == tenant_slug))
        ).scalar_one_or_none()
        if org is None:
            return None
        return (
            await session.execute(
                select(User).where(User.tenant_id == org.id, User.email == email)
            )
        ).scalar_one_or_none()
    # No tenant hint → platform user (SUPER_ADMIN).
    return (
        await session.execute(
            select(User).where(User.email == email, User.tenant_id.is_(None))
        )
    ).scalar_one_or_none()


async def _issue_tokens(session: AsyncSession, user: User, family: str | None = None) -> dict:
    access = create_access_token(user_id=user.id, role=user.role, tenant_id=user.tenant_id)
    refresh_plain = generate_refresh_token()
    token = RefreshToken(
        id=new_uuid(),
        user_id=user.id,
        tenant_id=user.tenant_id,
        token_hash=hash_refresh_token(refresh_plain),
        token_family=family or new_uuid(),
        expires_at=refresh_expiry(),
    )
    session.add(token)
    await session.flush()
    return {
        "access_token": access,
        "refresh_token": refresh_plain,
        "token_type": "bearer",
        "expires_in": settings.access_token_ttl_seconds,
        "role": user.role,
    }


async def login(session: AsyncSession, email: str, password: str, tenant_slug: str | None) -> dict:
    user = await _resolve_user(session, email, tenant_slug)
    # Constant-ish path: verify even when user missing to reduce enumeration.
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    if user.status != "ACTIVE":
        raise AppError(403, "USER_DISABLED", "Account is disabled")
    tokens = await _issue_tokens(session, user)
    await session.commit()
    return tokens


async def refresh(session: AsyncSession, refresh_token: str) -> dict:
    token_hash = hash_refresh_token(refresh_token)
    record = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()
    if record is None:
        raise AppError(401, "INVALID_REFRESH_TOKEN", "Unknown refresh token")

    now = datetime.now(timezone.utc)
    if record.revoked_at is not None:
        # Reuse of a revoked token → revoke the whole family (theft response).
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_family == record.token_family)
            .values(revoked_at=now)
        )
        await session.commit()
        raise AppError(401, "REFRESH_TOKEN_REUSED", "Refresh token reuse detected")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:  # naive (e.g. SQLite) → assume UTC
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise AppError(401, "REFRESH_TOKEN_EXPIRED", "Refresh token expired")

    user = (
        await session.execute(select(User).where(User.id == record.user_id))
    ).scalar_one_or_none()
    if user is None or user.status != "ACTIVE":
        raise AppError(401, "INVALID_REFRESH_TOKEN", "User no longer active")

    tokens = await _issue_tokens(session, user, family=record.token_family)
    record.revoked_at = now
    await session.commit()
    return tokens


async def logout(session: AsyncSession, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    record = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        await session.commit()


async def change_password(
    session: AsyncSession, user_id: str, current_password: str, new_password: str
) -> None:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise AppError(404, "NOT_FOUND", "User not found")
    if not verify_password(current_password, user.password_hash):
        raise AppError(400, "INVALID_PASSWORD", "Current password is incorrect")
    user.password_hash = hash_password(new_password)
    # Revoke all active refresh tokens on password change.
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await session.commit()
