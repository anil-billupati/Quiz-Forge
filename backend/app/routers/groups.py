"""Group endpoints — Org Admin (api-contracts Groups). Grouped contests, Draft."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.schemas.group import CreateGroupRequest, GroupOut, UpdateGroupRequest
from app.services import group_service as svc

router = APIRouter(prefix="/contests/{contest_id}/groups", tags=["Groups"])
_org_admin = require_roles("ORG_ADMIN")


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.post("", response_model=GroupOut, status_code=201)
async def create_group(
    contest_id: str,
    body: CreateGroupRequest,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> GroupOut:
    tenant_id = _require_tenant(principal)
    return GroupOut.model_validate(await svc.create_group(session, tenant_id, contest_id, body))


@router.get("", response_model=list[GroupOut])
async def list_groups(
    contest_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> list[GroupOut]:
    tenant_id = _require_tenant(principal)
    groups = await svc.list_groups(session, tenant_id, contest_id)
    return [GroupOut.model_validate(g) for g in groups]


@router.patch("/{group_id}", response_model=GroupOut)
async def update_group(
    contest_id: str,
    group_id: str,
    body: UpdateGroupRequest,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> GroupOut:
    tenant_id = _require_tenant(principal)
    group = await svc.update_group(session, tenant_id, contest_id, group_id, body)
    return GroupOut.model_validate(group)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    contest_id: str,
    group_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> Response:
    tenant_id = _require_tenant(principal)
    await svc.delete_group(session, tenant_id, contest_id, group_id)
    return Response(status_code=204)
