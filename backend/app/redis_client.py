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


# --- sorted-set helpers for the Leaderboard Engine (Unit 12) -----------------


async def zadd(key: str, mapping: dict[str, float]) -> int:
    """Add members to a sorted set; returns number of new members."""
    return await redis_client.zadd(key, mapping)


async def zrevrange(key: str, start: int = 0, stop: int = -1) -> list[str]:
    """Return members of a sorted set in descending score order."""
    return await redis_client.zrevrange(key, start, stop)


async def zrevrange_withscores(
    key: str, start: int = 0, stop: int = -1
) -> list[tuple[str, float]]:
    """Return members and scores in descending score order."""
    return await redis_client.zrevrange(key, start, stop, withscores=True)


async def zscore(key: str, member: str) -> float | None:
    """Return the score of a member, or None if absent."""
    return await redis_client.zscore(key, member)


async def zremrangebyrank(key: str, start: int, stop: int) -> int:
    """Remove members by rank range; returns number removed."""
    return await redis_client.zremrangebyrank(key, start, stop)


async def zrem(key: str, *members: str) -> int:
    """Remove specific members; returns number removed."""
    return await redis_client.zrem(key, *members)


async def hset(key: str, mapping: dict[str, str]) -> int:
    """Set fields in a hash."""
    return await redis_client.hset(key, mapping=mapping)


async def hgetall(key: str) -> dict[str, str]:
    """Return all fields of a hash."""
    return await redis_client.hgetall(key)


async def hmget(key: str, fields: list[str]) -> list[str | None]:
    """Return values for the given hash fields."""
    return await redis_client.hmget(key, fields)


async def delete_keys(*keys: str) -> int:
    """Delete one or more keys; returns number deleted."""
    if not keys:
        return 0
    return await redis_client.delete(*keys)
