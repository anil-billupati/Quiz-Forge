"""Execution control endpoints (api-contracts §Live runtime control).

Moderator / Org Admin actions that drive a Live contest. These mirror the WS
``moderator.*`` actions and exist for the moderator console and recovery.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.schemas.execution import AdvanceRequest, ExecutionStateResponse
from app.services import execution_service as svc

router = APIRouter(prefix="/contests/{contest_id}/control", tags=["Live"])
_controller = require_roles("ORG_ADMIN", "MODERATOR")


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.post("/start", response_model=ExecutionStateResponse)
async def start(
    contest_id: str,
    principal: Principal = Depends(_controller),
    session: AsyncSession = Depends(db_session),
) -> ExecutionStateResponse:
    tenant_id = _require_tenant(principal)
    await svc.start(session, tenant_id, contest_id)
    return ExecutionStateResponse(**await svc.snapshot(session, tenant_id, contest_id))


@router.post("/reveal", response_model=ExecutionStateResponse)
async def reveal(
    contest_id: str,
    principal: Principal = Depends(_controller),
    session: AsyncSession = Depends(db_session),
) -> ExecutionStateResponse:
    tenant_id = _require_tenant(principal)
    await svc.reveal(session, tenant_id, contest_id)
    return ExecutionStateResponse(**await svc.snapshot(session, tenant_id, contest_id))


@router.post("/advance", response_model=ExecutionStateResponse)
async def advance(
    contest_id: str,
    body: AdvanceRequest | None = None,
    principal: Principal = Depends(_controller),
    session: AsyncSession = Depends(db_session),
) -> ExecutionStateResponse:
    tenant_id = _require_tenant(principal)
    scope = body.scope if body is not None else "QUESTION"
    await svc.advance(session, tenant_id, contest_id, scope)
    return ExecutionStateResponse(**await svc.snapshot(session, tenant_id, contest_id))
