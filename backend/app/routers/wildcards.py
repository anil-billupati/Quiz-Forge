"""WildcardConfig endpoints (api-contracts Wildcards).

Org Admins enable/disable wildcards per ConfigurationBlock. Mutations are
allowed only while the parent contest is in DRAFT.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.schemas.wildcard import (
    WildcardConfigCreate,
    WildcardConfigResponse,
    WildcardConfigUpdate,
)
from app.services import wildcard_config_service as svc

router = APIRouter(tags=["Wildcards"])
_org_admin = require_roles("ORG_ADMIN")


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.post(
    "/configuration-blocks/{config_block_id}/wildcards",
    response_model=WildcardConfigResponse,
    status_code=201,
)
async def create_wildcard_config(
    config_block_id: str,
    body: WildcardConfigCreate,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> WildcardConfigResponse:
    tenant_id = _require_tenant(principal)
    config = await svc.create_wildcard_config(session, tenant_id, config_block_id, body)
    return WildcardConfigResponse.model_validate(config)


@router.get(
    "/configuration-blocks/{config_block_id}/wildcards",
    response_model=list[WildcardConfigResponse],
)
async def list_wildcard_configs(
    config_block_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> list[WildcardConfigResponse]:
    tenant_id = _require_tenant(principal)
    configs = await svc.list_wildcard_configs(session, tenant_id, config_block_id)
    return [WildcardConfigResponse.model_validate(c) for c in configs]


@router.get(
    "/configuration-blocks/{config_block_id}/wildcards/{wildcard_type}",
    response_model=WildcardConfigResponse,
)
async def get_wildcard_config(
    config_block_id: str,
    wildcard_type: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> WildcardConfigResponse:
    tenant_id = _require_tenant(principal)
    config = await svc.get_wildcard_config(session, tenant_id, config_block_id, wildcard_type)
    return WildcardConfigResponse.model_validate(config)


@router.patch(
    "/configuration-blocks/{config_block_id}/wildcards/{wildcard_type}",
    response_model=WildcardConfigResponse,
)
async def update_wildcard_config(
    config_block_id: str,
    wildcard_type: str,
    body: WildcardConfigUpdate,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> WildcardConfigResponse:
    tenant_id = _require_tenant(principal)
    config = await svc.update_wildcard_config(
        session, tenant_id, config_block_id, wildcard_type, body
    )
    return WildcardConfigResponse.model_validate(config)


@router.delete(
    "/configuration-blocks/{config_block_id}/wildcards/{wildcard_type}",
    status_code=204,
    response_model=None,
)
async def delete_wildcard_config(
    config_block_id: str,
    wildcard_type: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> None:
    tenant_id = _require_tenant(principal)
    await svc.delete_wildcard_config(session, tenant_id, config_block_id, wildcard_type)
