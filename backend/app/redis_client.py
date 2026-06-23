"""Redis client, readiness ping, and Streams command-bus helpers (ADR-002).

The engine workers consume commands from per-purpose Redis Streams. These
helpers are the foundation primitive; consumer-group wiring per engine is added
in the live-engine units (7–13).
"""
from __future__ import annotations

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def ping() -> bool:
    """Readiness check helper."""
    return bool(await redis_client.ping())


async def stream_publish(stream: str, fields: dict[str, str]) -> str:
    """Append an entry to a Redis Stream; returns the generated entry id."""
    return await redis_client.xadd(stream, fields)


async def stream_read(
    stream: str, last_id: str = "0", count: int = 100, block_ms: int | None = None
) -> list[tuple[str, dict[str, str]]]:
    """Read entries from a single stream after ``last_id`` (simple read)."""
    result = await redis_client.xread({stream: last_id}, count=count, block=block_ms)
    entries: list[tuple[str, dict[str, str]]] = []
    for _stream_name, items in result or []:
        entries.extend(items)
    return entries
