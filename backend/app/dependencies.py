"""Shared FastAPI dependencies: auth principal, RBAC, tenant context, paging.

Realises the §2.5 role-permission matrix. The access token's claims become the
:class:`Principal`; ``require_roles`` gates endpoints; tenant context is set from
the principal so downstream tenant-scoped queries are filtered (ADR-001).
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.middleware.errors import AppError
from app.middleware.tenant_context import reset_current_tenant, set_current_tenant
from app.security.tokens import TokenError, decode_access_token

# Registers the Bearer scheme so Swagger shows the "Authorize" button.
# auto_error=False so we can return our standard error envelope on 401.
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    """The authenticated caller, derived from JWT claims."""

    user_id: str
    role: str  # SUPER_ADMIN | ORG_ADMIN | MODERATOR | PARTICIPANT
    tenant_id: str | None  # None for SUPER_ADMIN


@dataclass
class PageParams:
    """Cursor pagination parameters (api-contracts.md §Pagination)."""

    limit: int = 50
    cursor: str | None = None


def page_params(
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None),
) -> PageParams:
    return PageParams(limit=limit, cursor=cursor)


async def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AsyncGenerator[Principal, None]:
    """Decode the bearer token, build the Principal, and set tenant context.

    Yields so the tenant context is reset when the request completes.
    """
    if credentials is None or not credentials.credentials:
        raise AppError(401, "UNAUTHORIZED", "Missing or invalid Authorization header")
    token = credentials.credentials
    try:
        claims = decode_access_token(token)
    except TokenError as exc:
        raise AppError(401, "UNAUTHORIZED", "Invalid or expired token", {"reason": str(exc)})

    principal = Principal(
        user_id=claims["sub"], role=claims["role"], tenant_id=claims.get("tenant_id")
    )
    ctx = set_current_tenant(principal.tenant_id)
    try:
        yield principal
    finally:
        reset_current_tenant(ctx)


def require_roles(*allowed: str):
    """Dependency factory enforcing the §2.5 role matrix for an endpoint."""

    async def _checker(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed:
            raise AppError(
                403,
                "FORBIDDEN",
                "Role not permitted for this operation",
                {"role": principal.role, "allowed": list(allowed)},
            )
        return principal

    return _checker


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session
