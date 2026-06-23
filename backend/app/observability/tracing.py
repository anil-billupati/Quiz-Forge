"""OpenTelemetry tracing baseline (technical-spec §6).

Instruments the FastAPI app. The concrete exporter (CloudWatch/OTLP) is supplied
per environment (ADR-003); when none is configured the SDK uses a no-op/console
provider so local and CI runs never fail on missing collectors.
"""
from __future__ import annotations

from fastapi import FastAPI


def configure_tracing(app: FastAPI, service_name: str) -> None:
    """Attach OpenTelemetry instrumentation if the SDK is available.

    Best-effort: tracing must never block app startup (resilience principle).
    """
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
    except Exception:  # noqa: BLE001 — observability is non-fatal at startup
        # No exporter/SDK in this environment; continue without tracing.
        pass
