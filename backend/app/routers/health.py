"""Ops endpoints: liveness and readiness (Unit 1)."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import redis_client
from app.db import engine
from sqlalchemy import text

router = APIRouter(tags=["Ops"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    """Readiness probe — checks PostgreSQL and Redis."""
    deps: dict[str, str] = {}
    ok = True

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        deps["postgres"] = "ok"
    except Exception:  # noqa: BLE001 — readiness must not raise
        deps["postgres"] = "unavailable"
        ok = False

    try:
        await redis_client.ping()
        deps["redis"] = "ok"
    except Exception:  # noqa: BLE001
        deps["redis"] = "unavailable"
        ok = False

    if ok:
        return JSONResponse({"status": "ready", "dependencies": deps})
    return JSONResponse(
        status_code=503,
        content={"error": {"code": "NOT_READY", "message": "Dependency unavailable", "details": deps}},
    )
