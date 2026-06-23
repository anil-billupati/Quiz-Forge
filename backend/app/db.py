"""Database engine, session, and tenant-scoping machinery (ADR-001, §7.1).

Two session-level hooks realise automatic tenant isolation:

* ``do_orm_execute`` — for SELECT/UPDATE/DELETE touching a ``TenantScoped``
  entity, a ``tenant_id`` filter is appended automatically. When enforcement is
  on and no tenant context is set, an :class:`UnscopedQueryError` is raised
  rather than silently returning cross-tenant rows.
* ``before_flush`` — newly added ``TenantScoped`` rows are stamped with the
  active ``tenant_id`` from request context, so it can never drift from the
  authoritative value or be set by the client.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, with_loader_criteria

from app.config import get_settings
from app.middleware.tenant_context import UnscopedQueryError, get_current_tenant
from app.models.base import TenantScoped

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_min,
    max_overflow=settings.db_pool_max - settings.db_pool_min,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(execute_state) -> None:
    """Append a tenant_id filter to tenant-scoped SELECT/UPDATE/DELETE."""
    if not (
        execute_state.is_select
        or execute_state.is_update
        or execute_state.is_delete
    ):
        return
    # Skip queries that don't touch a tenant-scoped entity.
    if not _touches_tenant_scoped(execute_state):
        return

    tenant_id = get_current_tenant()
    if tenant_id is None:
        if settings.enforce_query_scoping:
            raise UnscopedQueryError(
                "Tenant-scoped query executed with no tenant context set."
            )
        return

    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantScoped,
            lambda cls: cls.tenant_id == tenant_id,
            include_aliases=True,
        )
    )


def _touches_tenant_scoped(execute_state) -> bool:
    for mapper in execute_state.all_mappers:
        if issubclass(mapper.class_, TenantScoped):
            return True
    return False


@event.listens_for(Session, "before_flush")
def _stamp_tenant_id(session: Session, _flush_context, _instances) -> None:
    """Stamp tenant_id on new tenant-scoped rows from request context."""
    tenant_id = get_current_tenant()
    for obj in session.new:
        if isinstance(obj, TenantScoped):
            current = getattr(obj, "tenant_id", None)
            if current is None:
                if tenant_id is None and settings.enforce_query_scoping:
                    raise UnscopedQueryError(
                        "Insert of a tenant-scoped row with no tenant context set."
                    )
                obj.tenant_id = tenant_id  # type: ignore[assignment]


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a scoped DB session."""
    async with SessionLocal() as session:
        yield session
