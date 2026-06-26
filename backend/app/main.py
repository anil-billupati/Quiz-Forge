"""ContestForge API service entry point.

Scaffold only — routers and engines are implemented per the delivery plan
(docs/plan/delivery-plan.md), starting with Unit 1 (Platform foundation).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.middleware.errors import register_exception_handlers
from app.middleware.logging import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.tenant_context import TenantContextMiddleware
from app.observability.tracing import configure_tracing
from app.realtime.gateway import start_subscriber, stop_subscriber
from app.routers import (
    auth,
    configurations,
    contests,
    control,
    groups,
    health,
    leaderboard,
    live,
    organizations,
    questions,
    registrations,
    users,
    wildcards,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cross-instance live fan-out; resilient if Redis is unavailable (Unit 7).
    await start_subscriber()
    try:
        yield
    finally:
        await stop_subscriber()


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    app = FastAPI(
        title="ContestForge Core Contest Engine API",
        version="1.0.0",
        description="Multi-tenant live contest engine. See docs/spec/api-contracts.yaml.",
        lifespan=lifespan,
    )

    # Tenant context is established per request (ADR-001); JWT population in Unit 2.
    app.add_middleware(TenantContextMiddleware)
    # Outermost: log request start/end and bind a correlation id for all logs.
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)
    configure_tracing(app, settings.service_name)

    # Ops endpoints (Unit 1). Resource routers are registered as units land.
    app.include_router(health.router)
    # Unit 2 — Tenancy & Identity.
    app.include_router(auth.router)
    app.include_router(organizations.router)
    app.include_router(users.router)
    # Unit 3 — Contest authoring: lifecycle (F6) + groups (F7) + config blocks (F8) + wildcards (F9).
    app.include_router(contests.router)
    app.include_router(groups.router)
    app.include_router(configurations.router)
    app.include_router(wildcards.router)
    # Unit 5 — Questions & options (F-authoring).
    app.include_router(questions.router)
    # Unit 6 — Registration.
    app.include_router(registrations.router)
    # Unit 7 — Real-time foundation (WebSocket gateway + live-state).
    app.include_router(live.router)
    # Unit 8 — Execution Engine (moderator control endpoints).
    app.include_router(control.router)
    # Unit 12 — Leaderboard Engine.
    app.include_router(leaderboard.router)

    return app


app = create_app()
