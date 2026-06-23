"""Shared pytest fixtures.

Integration fixtures spin up Postgres/Redis via testcontainers
(docs/spec/testing-strategy.md §2.2). Added in Unit 1.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
