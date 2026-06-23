"""Contest endpoints — Org Admin (api-contracts Contests / Lifecycle)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.schemas.contest import (
    ContestOut,
    CreateContestRequest,
    LifecycleTransitionRequest,
    UpdateContestRequest,
)
from app.services import contest_service as svc

router = APIRouter(prefix="/contests", tags=["Contests"])
_org_admin = require_roles("ORG_ADMIN")


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.post("", response_model=ContestOut, status_code=201)
async def create_contest(
    body: CreateContestRequest,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ContestOut:
    tenant_id = _require_tenant(principal)
    contest = await svc.create_contest(session, tenant_id, body, created_by=principal.user_id)
    return ContestOut.model_validate(contest)


@router.get("", response_model=list[ContestOut])
async def list_contests(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> list[ContestOut]:
    tenant_id = _require_tenant(principal)
    contests = await svc.list_contests(session, tenant_id, status=status, limit=limit)
    return [ContestOut.model_validate(c) for c in contests]


@router.get("/{contest_id}", response_model=ContestOut)
async def get_contest(
    contest_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ContestOut:
    tenant_id = _require_tenant(principal)
    return ContestOut.model_validate(await svc.get_contest(session, tenant_id, contest_id))


@router.patch("/{contest_id}", response_model=ContestOut)
async def update_contest(
    contest_id: str,
    body: UpdateContestRequest,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ContestOut:
    tenant_id = _require_tenant(principal)
    return ContestOut.model_validate(await svc.update_contest(session, tenant_id, contest_id, body))


@router.delete("/{contest_id}", status_code=204)
async def delete_contest(
    contest_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> Response:
    tenant_id = _require_tenant(principal)
    await svc.delete_contest(session, tenant_id, contest_id)
    return Response(status_code=204)


@router.post("/{contest_id}/lifecycle", response_model=ContestOut)
async def transition_lifecycle(
    contest_id: str,
    body: LifecycleTransitionRequest,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ContestOut:
    tenant_id = _require_tenant(principal)
    contest = await svc.transition_lifecycle(
        session,
        tenant_id,
        contest_id,
        target_status=body.target_status,
        scheduled_start_at=body.scheduled_start_at,
        triggered_by=principal.user_id,
    )
    return ContestOut.model_validate(contest)
