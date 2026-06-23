"""Organization (tenant) management service (FR-1/2/3a/3b, BR-19).

Creating an organization atomically provisions the tenant, its default
TenantSettings, and the initial Org Admin. slug/portal_url are unique and
immutable once the tenant has published a contest (BR-19).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.organization import Organization, TenantSettings
from app.models.tenant_usage import TenantUsageRecord
from app.models.user import User
from app.schemas.organization import (
    CreateOrganizationRequest,
    TenantSettingsPatch,
    UpdateOrganizationRequest,
)
from app.security.passwords import hash_password


async def create_organization(
    session: AsyncSession, payload: CreateOrganizationRequest, created_by: str | None
) -> Organization:
    org = Organization(
        id=new_uuid(),
        slug=payload.slug,
        name=payload.name,
        portal_url=payload.portal_url,
        custom_domain=payload.custom_domain,
        created_by=created_by,
    )
    session.add(org)
    session.add(TenantSettings(organization_id=org.id))
    session.add(
        User(
            id=new_uuid(),
            tenant_id=org.id,
            email=payload.admin_email,
            password_hash=hash_password(payload.admin_password),
            role="ORG_ADMIN",
            first_name=payload.admin_first_name,
            last_name=payload.admin_last_name,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AppError(
            409, "CONFLICT", "slug, portal_url, or custom_domain already in use"
        )
    await session.refresh(org)
    return org


async def list_organizations(
    session: AsyncSession, *, status: str | None, limit: int
) -> list[Organization]:
    stmt = select(Organization)
    if status:
        stmt = stmt.where(Organization.status == status)
    stmt = stmt.order_by(Organization.created_at).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_organization(session: AsyncSession, org_id: str) -> Organization:
    org = (
        await session.execute(select(Organization).where(Organization.id == org_id))
    ).scalar_one_or_none()
    if org is None:
        raise AppError(404, "NOT_FOUND", "Organization not found")
    return org


async def update_organization(
    session: AsyncSession, org_id: str, payload: UpdateOrganizationRequest
) -> Organization:
    org = await get_organization(session, org_id)
    # slug/portal_url are immutable (BR-19) and intentionally not accepted here.
    if payload.name is not None:
        org.name = payload.name
    if payload.custom_domain is not None:
        org.custom_domain = payload.custom_domain
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AppError(409, "CONFLICT", "custom_domain already in use")
    await session.refresh(org)
    return org


async def set_status(session: AsyncSession, org_id: str, status: str) -> Organization:
    if status not in ("ACTIVE", "SUSPENDED"):
        raise AppError(422, "INVALID_STATUS", "Status must be ACTIVE or SUSPENDED")
    org = await get_organization(session, org_id)
    org.status = status
    await session.commit()
    await session.refresh(org)
    return org


async def get_settings_for(session: AsyncSession, org_id: str) -> TenantSettings:
    await get_organization(session, org_id)  # 404 if org missing
    settings_row = (
        await session.execute(
            select(TenantSettings).where(TenantSettings.organization_id == org_id)
        )
    ).scalar_one_or_none()
    if settings_row is None:
        raise AppError(404, "NOT_FOUND", "Tenant settings not found")
    return settings_row


async def update_settings(
    session: AsyncSession, org_id: str, patch: TenantSettingsPatch
) -> TenantSettings:
    settings_row = await get_settings_for(session, org_id)
    data = patch.model_dump(exclude_unset=True)
    if not data:
        raise AppError(422, "EMPTY_PATCH", "At least one setting must be provided")
    for field, value in data.items():
        setattr(settings_row, field, value)
    await session.commit()
    await session.refresh(settings_row)
    return settings_row


async def get_usage(session: AsyncSession, org_id: str) -> TenantUsageRecord:
    """Return the latest usage record, or a zeroed current-period record.

    Unit 2 establishes the read path; later units increment the counters.
    """
    await get_organization(session, org_id)
    record = (
        await session.execute(
            select(TenantUsageRecord)
            .where(TenantUsageRecord.tenant_id == org_id)
            .order_by(TenantUsageRecord.period_start.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if record is not None:
        return record
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return TenantUsageRecord(
        id=new_uuid(), tenant_id=org_id, period_start=period_start, period_end=now
    )
