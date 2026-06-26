"""Single-use WebSocket connection tickets (api-contracts §WebSocket).

Browsers cannot set an Authorization header on a WS handshake, so the client
first exchanges its bearer token for a short-lived, single-use ticket via REST,
then presents the ticket as a subprotocol on connect. The ticket is bound to the
user + contest and consumed on first use.

The default store is in-process, which is correct for a single instance and for
tests. A Redis-backed store (keys with TTL, ``GETDEL`` on consume) is the path to
multi-instance ticket sharing (ADR-003) and can replace this without touching
callers.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from app.config import get_settings


@dataclass(frozen=True)
class TicketPayload:
    user_id: str
    role: str
    tenant_id: str
    contest_id: str


class InMemoryTicketStore:
    """Best-effort single-use ticket store with TTL (single-process)."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._tickets: dict[str, tuple[TicketPayload, float]] = {}

    def issue(self, payload: TicketPayload) -> str:
        # token_urlsafe yields URL-safe chars only (no '.'), so it is safe to
        # carry inside the ``ticket.<value>`` subprotocol token.
        token = secrets.token_urlsafe(24)
        self._tickets[token] = (payload, time.monotonic() + self._ttl)
        return token

    def consume(self, token: str) -> TicketPayload | None:
        item = self._tickets.pop(token, None)
        if item is None:
            return None
        payload, expires_at = item
        if time.monotonic() > expires_at:
            return None
        return payload


ticket_store = InMemoryTicketStore(get_settings().live_ticket_ttl_seconds)
