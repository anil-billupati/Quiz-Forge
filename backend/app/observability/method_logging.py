"""Method entry/exit logging (technical-spec §6).

Provides a single ``@logged`` decorator that emits a structured log line when a
function is entered and another when it returns (or raises), including the
elapsed time. Works transparently on both ``async def`` and plain ``def``
callables so it can be applied uniformly across services, helpers, and any
future implementation.

Usage::

    from app.observability.method_logging import logged

    @logged
    async def create_group(session, tenant_id, contest_id, payload):
        ...

The decorator deliberately does NOT log argument values by default: service
methods receive sessions, principals, and password payloads that must not reach
the logs (security baseline). Pass ``log_args=True`` only for callables whose
arguments are known to be safe.
"""
from __future__ import annotations

import functools
import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar

import structlog

F = TypeVar("F", bound=Callable[..., Any])

# Argument names that must never be rendered into logs even when log_args=True.
_SENSITIVE_ARGS = frozenset(
    {"password", "new_password", "old_password", "token", "secret", "session"}
)


def _safe_arg_repr(name: str, value: Any) -> str:
    if name in _SENSITIVE_ARGS:
        return "<redacted>"
    text = repr(value)
    return text if len(text) <= 200 else f"{text[:200]}…"


def logged(func: F | None = None, *, log_args: bool = False) -> F | Callable[[F], F]:
    """Log entry and exit (with duration) for the decorated callable.

    Can be used bare (``@logged``) or with options (``@logged(log_args=True)``).
    Emits ``method.enter`` on entry and ``method.exit`` on success, or
    ``method.error`` if the call raises. The exception is re-raised unchanged.
    """

    def decorate(target: F) -> F:
        logger = structlog.get_logger(target.__module__)
        method = target.__qualname__
        sig = inspect.signature(target) if log_args else None

        def _bind_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, str]:
            if sig is None:
                return {}
            try:
                bound = sig.bind_partial(*args, **kwargs)
            except TypeError:
                return {}
            return {name: _safe_arg_repr(name, val) for name, val in bound.arguments.items()}

        if inspect.iscoroutinefunction(target):

            @functools.wraps(target)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                logger.info("method.enter", method=method, **_bind_args(args, kwargs))
                start = time.perf_counter()
                try:
                    result = await target(*args, **kwargs)
                except Exception as exc:
                    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                    logger.error(
                        "method.error",
                        method=method,
                        duration_ms=elapsed_ms,
                        error=type(exc).__name__,
                    )
                    raise
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.info("method.exit", method=method, duration_ms=elapsed_ms)
                return result

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(target)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info("method.enter", method=method, **_bind_args(args, kwargs))
            start = time.perf_counter()
            try:
                result = target(*args, **kwargs)
            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.error(
                    "method.error",
                    method=method,
                    duration_ms=elapsed_ms,
                    error=type(exc).__name__,
                )
                raise
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info("method.exit", method=method, duration_ms=elapsed_ms)
            return result

        return sync_wrapper  # type: ignore[return-value]

    # Bare @logged vs parameterized @logged(...)
    if func is not None:
        return decorate(func)
    return decorate
