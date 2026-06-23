"""Foundation DB integration test (technical-spec §2.2).

Spins up real PostgreSQL via testcontainers, runs the scoping machinery against
it, and confirms the tenant-scoped probe table behaves as designed. Marked
``integration`` — requires Docker.
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

import app.db  # noqa: F401 — registers scoping events

pytestmark = pytest.mark.integration


@pytest.fixture
async def pg_session():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as pg:
        url = pg.get_connection_url().replace("psycopg2", "asyncpg")
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as s:
            yield s
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_rows_are_isolated(pg_session):
    for tenant, label in [("t1", "one"), ("t2", "two")]:
        token = set_current_tenant(tenant)
        try:
            pg_session.add(FoundationProbe(label=label))
            await pg_session.commit()
        finally:
            reset_current_tenant(token)

    token = set_current_tenant("t1")
    try:
        rows = (await pg_session.execute(select(FoundationProbe))).scalars().all()
    finally:
        reset_current_tenant(token)

    assert [r.label for r in rows] == ["one"]


@pytest.mark.asyncio
async def test_unscoped_query_rejected_on_postgres(pg_session):
    with pytest.raises(UnscopedQueryError):
        await pg_session.execute(select(FoundationProbe))
