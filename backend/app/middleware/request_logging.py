"""Request entry/exit logging (technical-spec §6).

ASGI middleware that emits a ``request.start`` log when an HTTP request is
received and a ``request.end`` log when the response is sent, including the
status code and elapsed time. A per-request ``request_id`` is bound into the
structlog context so every ``method.enter``/``method.exit`` line produced by the
``@logged`` decorator during the request carries the same id and can be
correlated.
"""
from __future__ import annotations

import time

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.models.base import new_uuid

logger = structlog.get_logger("app.request")


class RequestLoggingMiddleware:
    """Log the start and end of every HTTP request with a correlation id."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = new_uuid()
        method = scope.get("method", "")
        path = scope.get("path", "")

        # Bind the correlation id for the duration of this request so every
        # downstream log line (method.enter/exit, app logs) carries it.
        structlog.contextvars.bind_contextvars(request_id=request_id)
        logger.info("request.start", method=method, path=path)
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "request.end", method=method, path=path, status=500, duration_ms=elapsed_ms
            )
            raise
        else:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request.end",
                method=method,
                path=path,
                status=status_code,
                duration_ms=elapsed_ms,
            )
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
