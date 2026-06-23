"""Tenant-scoping machinery tests (ADR-001, technical-spec §7.1).

Uses in-memory SQLite so the mixin filter, auto-stamping, and unscoped-query
assertion are validated without Docker. Postgres-specific RLS is covered by the
integration suite.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.middleware.tenant_context import (
    UnscopedQueryError,
    reset_current_tenant,
    set_current_tenant,
)
from app.models.base import Base
from app.models.foundation_probe import FoundationProbe

# Importing app.db registers the session-level scoping events globally.
import app.db  # noqa: F401


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _seed(session, tenant_id: str, label: str) -> None:
    token = set_current_tenant(tenant_id)
    try:
        session.add(FoundationProbe(label=label))
        await session.commit()
    finally:
        reset_current_tenant(token)


@pytest.mark.asyncio
async def test_insert_autostamps_tenant_id(session):
    await _seed(session, "tenant-a", "alpha")
    token = set_current_tenant("tenant-a")
    try:
        rows = (await session.execute(select(FoundationProbe))).scalars().all()
    finally:
        reset_current_tenant(token)
    assert len(rows) == 1
    assert rows[0].tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_query_is_filtered_by_tenant(session):
    await _seed(session, "tenant-a", "alpha")
    await _seed(session, "tenant-b", "beta")

    token = set_current_tenant("tenant-a")
    try:
        rows = (await session.execute(select(FoundationProbe))).scalars().all()
    finally:
        reset_current_tenant(token)

    assert [r.label for r in rows] == ["alpha"]  # tenant-b row is invisible


@pytest.mark.asyncio
async def test_unscoped_query_raises(session):
    await _seed(session, "tenant-a", "alpha")
    # No tenant context set → enforcement must reject the query.
    with pytest.raises(UnscopedQueryError):
        await session.execute(select(FoundationProbe))


@pytest.mark.asyncio
async def test_unscoped_insert_raises(session):
    with pytest.raises(UnscopedQueryError):
        session.add(FoundationProbe(label="orphan"))
        await session.flush()
