"""Tenant context plumbing (ADR-001, technical-spec §7.1).

Resolves the active ``tenant_id`` for the duration of a request and exposes it
via a context variable. The session machinery in ``app.db`` reads this to scope
every tenant-scoped query and to stamp ``tenant_id`` on insert.

JWT-based population is implemented in Unit 2 (Tenancy & Identity). This module
provides the context primitive and an ASGI middleware that establishes and
tears down the context per request; until Unit 2 lands it reads an explicit
``X-Tenant-Id`` header (used only in tests/local), never trusting it in
production paths.
"""
from __future__ import annotations

from contextvars import ContextVar

from starlette.types import ASGIApp, Receive, Scope, Send

# None => platform-scoped (SUPER_ADMIN) or unauthenticated context.
_current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)


class UnscopedQueryError(RuntimeError):
    """Raised when a tenant-scoped query runs with no tenant context set."""


def set_current_tenant(tenant_id: str | None) -> object:
    """Set the active tenant; returns a token for :func:`reset_current_tenant`."""
    return _current_tenant_id.set(tenant_id)


def reset_current_tenant(token: object) -> None:
    _current_tenant_id.reset(token)  # type: ignore[arg-type]


def get_current_tenant() -> str | None:
    return _current_tenant_id.get()


class TenantContextMiddleware:
    """ASGI middleware that scopes the tenant context to each request.

    Unit 1 establishes/tears down the context. Unit 2 replaces the header read
    with verified JWT claims.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        tenant_id: str | None = None
        for key, value in scope.get("headers", []):
            if key == b"x-tenant-id":
                tenant_id = value.decode() or None
                break

        token = set_current_tenant(tenant_id)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_current_tenant(token)
