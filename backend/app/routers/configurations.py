"""ConfigurationBlock endpoints (api-contracts Configurations).

Org Admins configure how a contest or group is run and scored. Configuration is
editable only while the parent contest is in DRAFT.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.schemas.configuration import (
    ConfigurationBlockCreate,
    ConfigurationBlockResponse,
    ConfigurationBlockUpdate,
)
from app.services import configuration_service as svc

router = APIRouter(tags=["Configurations"])
_org_admin = require_roles("ORG_ADMIN")


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.put("/contests/{contest_id}/configuration", response_model=ConfigurationBlockResponse)
async def set_contest_configuration(
    contest_id: str,
    body: ConfigurationBlockCreate,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ConfigurationBlockResponse:
    tenant_id = _require_tenant(principal)
    block = await svc.create_or_replace_contest_block(session, tenant_id, contest_id, body)
    return ConfigurationBlockResponse.model_validate(block)


@router.get("/contests/{contest_id}/configuration", response_model=ConfigurationBlockResponse)
async def get_contest_configuration(
    contest_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ConfigurationBlockResponse:
    tenant_id = _require_tenant(principal)
    block = await svc.get_contest_block(session, tenant_id, contest_id)
    return ConfigurationBlockResponse.model_validate(block)


@router.patch("/contests/{contest_id}/configuration", response_model=ConfigurationBlockResponse)
async def update_contest_configuration(
    contest_id: str,
    body: ConfigurationBlockUpdate,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ConfigurationBlockResponse:
    tenant_id = _require_tenant(principal)
    block = await svc.update_contest_block(session, tenant_id, contest_id, body)
    return ConfigurationBlockResponse.model_validate(block)


@router.put(
    "/contests/{contest_id}/groups/{group_id}/configuration",
    response_model=ConfigurationBlockResponse,
)
async def set_group_configuration(
    contest_id: str,
    group_id: str,
    body: ConfigurationBlockCreate,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ConfigurationBlockResponse:
    tenant_id = _require_tenant(principal)
    block = await svc.create_or_replace_group_block(session, tenant_id, contest_id, group_id, body)
    return ConfigurationBlockResponse.model_validate(block)


@router.get(
    "/contests/{contest_id}/groups/{group_id}/configuration",
    response_model=ConfigurationBlockResponse,
)
async def get_group_configuration(
    contest_id: str,
    group_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ConfigurationBlockResponse:
    tenant_id = _require_tenant(principal)
    block = await svc.get_group_block(session, tenant_id, contest_id, group_id)
    return ConfigurationBlockResponse.model_validate(block)


@router.patch(
    "/contests/{contest_id}/groups/{group_id}/configuration",
    response_model=ConfigurationBlockResponse,
)
async def update_group_configuration(
    contest_id: str,
    group_id: str,
    body: ConfigurationBlockUpdate,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> ConfigurationBlockResponse:
    tenant_id = _require_tenant(principal)
    block = await svc.update_group_block(session, tenant_id, contest_id, group_id, body)
    return ConfigurationBlockResponse.model_validate(block)
