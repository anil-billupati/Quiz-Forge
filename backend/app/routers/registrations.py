"""Registration endpoints (api-contracts Registration).

Participants self-register and withdraw; Org Admins / Moderators list the roster.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.schemas.registration import RegistrationResponse
from app.services import registration_service as svc

router = APIRouter(prefix="/contests/{contest_id}/registrations", tags=["Registration"])
_participant = require_roles("PARTICIPANT")
_staff = require_roles("ORG_ADMIN", "MODERATOR")
_self_or_admin = require_roles("PARTICIPANT", "ORG_ADMIN")


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.post("", response_model=RegistrationResponse, status_code=201)
async def register(
    contest_id: str,
    principal: Principal = Depends(_participant),
    session: AsyncSession = Depends(db_session),
) -> RegistrationResponse:
    tenant_id = _require_tenant(principal)
    registration = await svc.register(session, tenant_id, contest_id, principal.user_id)
    return RegistrationResponse.model_validate(registration)


@router.get("", response_model=list[RegistrationResponse])
async def list_registrations(
    contest_id: str,
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    principal: Principal = Depends(_staff),
    session: AsyncSession = Depends(db_session),
) -> list[RegistrationResponse]:
    tenant_id = _require_tenant(principal)
    rows = await svc.list_registrations(
        session, tenant_id, contest_id, status=status, limit=limit
    )
    return [RegistrationResponse.model_validate(r) for r in rows]


@router.get("/me", response_model=RegistrationResponse)
async def get_my_registration(
    contest_id: str,
    principal: Principal = Depends(_participant),
    session: AsyncSession = Depends(db_session),
) -> RegistrationResponse:
    tenant_id = _require_tenant(principal)
    registration = await svc.get_my_registration(session, tenant_id, contest_id, principal.user_id)
    return RegistrationResponse.model_validate(registration)


@router.delete("/{registration_id}", status_code=204)
async def withdraw(
    contest_id: str,
    registration_id: str,
    principal: Principal = Depends(_self_or_admin),
    session: AsyncSession = Depends(db_session),
) -> Response:
    tenant_id = _require_tenant(principal)
    await svc.withdraw(
        session,
        tenant_id,
        contest_id,
        registration_id,
        actor_id=principal.user_id,
        actor_role=principal.role,
    )
    return Response(status_code=204)
