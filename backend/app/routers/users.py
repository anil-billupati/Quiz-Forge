"""User endpoints (api-contracts Users). Org Admin manages tenant users;
Super Admin creates other Super Admins."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.schemas.user import (
    CreateSuperAdminRequest,
    CreateUserRequest,
    UpdateUserRequest,
    UserOut,
)
from app.services import user_service as svc

router = APIRouter(tags=["Users"])
_org_admin = require_roles("ORG_ADMIN")
_super_admin = require_roles("SUPER_ADMIN")


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    body: CreateUserRequest,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> UserOut:
    tenant_id = _require_tenant(principal)
    return UserOut.model_validate(await svc.create_user(session, tenant_id, body))


@router.get("/users", response_model=list[UserOut])
async def list_users(
    role: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> list[UserOut]:
    tenant_id = _require_tenant(principal)
    users = await svc.list_users(session, tenant_id, role=role, status=status, limit=limit)
    return [UserOut.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> UserOut:
    tenant_id = _require_tenant(principal)
    return UserOut.model_validate(await svc.get_user(session, tenant_id, user_id))


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> UserOut:
    tenant_id = _require_tenant(principal)
    return UserOut.model_validate(await svc.update_user(session, tenant_id, user_id, body))


@router.post("/super-admins", response_model=UserOut, status_code=201, tags=["Users"])
async def create_super_admin(
    body: CreateSuperAdminRequest,
    _: Principal = Depends(_super_admin),
    session: AsyncSession = Depends(db_session),
) -> UserOut:
    return UserOut.model_validate(await svc.create_super_admin(session, body))
