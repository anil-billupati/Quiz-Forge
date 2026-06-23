"""Organization endpoints — Super Admin only (api-contracts Organizations)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.schemas.organization import (
    CreateOrganizationRequest,
    OrganizationOut,
    OrganizationStatusPatch,
    TenantSettingsOut,
    TenantSettingsPatch,
    TenantUsageOut,
    UpdateOrganizationRequest,
)
from app.services import organization_service as svc

router = APIRouter(prefix="/organizations", tags=["Organizations"])
_super_admin = require_roles("SUPER_ADMIN")


@router.post("", response_model=OrganizationOut, status_code=201)
async def create_org(
    body: CreateOrganizationRequest,
    principal: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(db_session),
) -> OrganizationOut:
    org = await svc.create_organization(session, body, created_by=principal.user_id)
    return OrganizationOut.model_validate(org)


@router.get("", response_model=list[OrganizationOut])
async def list_orgs(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(db_session),
) -> list[OrganizationOut]:
    orgs = await svc.list_organizations(session, status=status, limit=limit)
    return [OrganizationOut.model_validate(o) for o in orgs]


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_org(
    org_id: str,
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(db_session),
) -> OrganizationOut:
    return OrganizationOut.model_validate(await svc.get_organization(session, org_id))


@router.patch("/{org_id}", response_model=OrganizationOut)
async def update_org(
    org_id: str,
    body: UpdateOrganizationRequest,
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(db_session),
) -> OrganizationOut:
    return OrganizationOut.model_validate(await svc.update_organization(session, org_id, body))


@router.patch("/{org_id}/status", response_model=OrganizationOut)
async def set_org_status(
    org_id: str,
    body: OrganizationStatusPatch,
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(db_session),
) -> OrganizationOut:
    return OrganizationOut.model_validate(await svc.set_status(session, org_id, body.status))


@router.get("/{org_id}/settings", response_model=TenantSettingsOut)
async def get_settings(
    org_id: str,
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(db_session),
) -> TenantSettingsOut:
    return TenantSettingsOut.model_validate(await svc.get_settings_for(session, org_id))


@router.patch("/{org_id}/settings", response_model=TenantSettingsOut)
async def update_settings(
    org_id: str,
    body: TenantSettingsPatch,
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(db_session),
) -> TenantSettingsOut:
    return TenantSettingsOut.model_validate(await svc.update_settings(session, org_id, body))


@router.get("/{org_id}/usage", response_model=TenantUsageOut)
async def get_usage(
    org_id: str,
    period: str | None = Query(None),
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(db_session),
) -> TenantUsageOut:
    return TenantUsageOut.model_validate(await svc.get_usage(session, org_id))
