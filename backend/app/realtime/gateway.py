"""Connection registry and per-contest event fan-out (Unit 7, technical-spec §3).

Each app instance keeps an in-process registry of live WebSocket connections per
contest and delivers events to them directly. For horizontal scale (ADR-003),
``publish_event`` also publishes to a Redis channel; a per-instance subscriber
re-broadcasts messages that originated on *other* instances (deduplicated by an
``_origin`` tag), so a client connected to any instance receives every event
exactly once. Presence is tracked best-effort in Redis.

Redis is best-effort here: if it is unavailable the gateway still works for a
single instance (local delivery), which keeps the fast test suite Redis-free.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from typing import Any

import structlog
from starlette.websockets import WebSocket

from app.redis_client import redis_client

logger = structlog.get_logger("app.realtime")

# Identifies this process so the subscriber can skip its own published messages.
INSTANCE_ID = uuid.uuid4().hex


def _channel(contest_id: str) -> str:
    return f"live:contest:{contest_id}"


def _presence_key(contest_id: str) -> str:
    return f"live:presence:{contest_id}"


class ConnectionManager:
    """In-process registry of live connections, grouped per contest.

    Each socket is annotated with the authenticated user id so that ``MASKED``
    leaderboard pushes can deliver a personalized payload per participant.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._meta: dict[WebSocket, dict[str, Any]] = {}

    async def connect(
        self,
        contest_id: str,
        websocket: WebSocket,
        user_id: str | None = None,
        role: str | None = None,
    ) -> None:
        self._rooms.setdefault(contest_id, set()).add(websocket)
        self._meta[websocket] = {"user_id": user_id, "role": role}

    def disconnect(self, contest_id: str, websocket: WebSocket) -> None:
        room = self._rooms.get(contest_id)
        if room is None:
            return
        room.discard(websocket)
        self._meta.pop(websocket, None)
        if not room:
            self._rooms.pop(contest_id, None)

    async def broadcast(self, contest_id: str, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for websocket in list(self._rooms.get(contest_id, ())):
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(contest_id, websocket)

    def local_count(self, contest_id: str) -> int:
        return len(self._rooms.get(contest_id, ()))

    def connections(self, contest_id: str) -> list[tuple[WebSocket, dict[str, Any]]]:
        """Return all connected sockets in a contest with their metadata."""
        return [
            (ws, self._meta.get(ws, {}))
            for ws in self._rooms.get(contest_id, ())
        ]

    async def broadcast_personalized(
        self,
        contest_id: str,
        payload_fn: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Send a per-socket payload computed from the socket's metadata.

        Used by MASKED leaderboard visibility so each participant receives only
        their own entry while admins/moderators can still receive the full board.
        """
        dead: list[WebSocket] = []
        for websocket, meta in self.connections(contest_id):
            try:
                await websocket.send_json(payload_fn(meta))
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(contest_id, websocket)


manager = ConnectionManager()


async def add_presence(contest_id: str, user_id: str) -> None:
    try:
        await redis_client.sadd(_presence_key(contest_id), user_id)
    except Exception:
        logger.warning("presence.add_failed", contest_id=contest_id)


async def remove_presence(contest_id: str, user_id: str) -> None:
    try:
        await redis_client.srem(_presence_key(contest_id), user_id)
    except Exception:
        logger.warning("presence.remove_failed", contest_id=contest_id)


async def publish_event(contest_id: str, event: dict[str, Any]) -> None:
    """Deliver an event to all connected clients of a contest (any instance)."""
    # Best-effort cross-instance publish; tagged so we don't double-deliver locally.
    try:
        await redis_client.publish(_channel(contest_id), json.dumps({**event, "_origin": INSTANCE_ID}))
    except Exception:
        logger.warning("publish.redis_failed", contest_id=contest_id)
    # Local delivery happens here regardless of Redis availability.
    await manager.broadcast(contest_id, event)


_subscriber_task: asyncio.Task | None = None


async def _run_subscriber() -> None:
    """Re-broadcast events published by other instances to local connections."""
    try:
        pubsub = redis_client.pubsub()
        await pubsub.psubscribe(_channel("*"))
        async for message in pubsub.listen():
            if message.get("type") != "pmessage":
                continue
            try:
                data = json.loads(message["data"])
            except (ValueError, TypeError):
                continue
            if data.pop("_origin", None) == INSTANCE_ID:
                continue  # already delivered locally by publish_event
            contest_id = str(message["channel"]).split(":")[-1]
            await manager.broadcast(contest_id, data)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # Redis down / connection lost: run local-only.
        logger.warning("subscriber.stopped", error=str(exc))


async def start_subscriber() -> None:
    global _subscriber_task
    if _subscriber_task is None:
        _subscriber_task = asyncio.create_task(_run_subscriber())


async def stop_subscriber() -> None:
    global _subscriber_task
    if _subscriber_task is not None:
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
        _subscriber_task = None
