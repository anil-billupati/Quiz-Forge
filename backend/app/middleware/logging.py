"""Structured JSON logging (technical-spec §6)."""
import logging

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog for JSON output with correlation/tenant context."""
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


def get_logger(name: str | None = None):
    return structlog.get_logger(name)
