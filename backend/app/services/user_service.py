"""User management service (FR-5, §2.5).

Org Admins create/list/manage users within their own tenant. SUPER_ADMIN is
never creatable here (use create_super_admin). All queries are explicitly scoped
to the caller's tenant because User carries a nullable tenant_id and is not
covered by the automatic scoping mixin.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.user import ROLES, User
from app.schemas.user import CreateSuperAdminRequest, CreateUserRequest, UpdateUserRequest
from app.security.passwords import hash_password

TENANT_CREATABLE_ROLES = ("ORG_ADMIN", "MODERATOR", "PARTICIPANT")


async def _email_taken(session: AsyncSession, tenant_id: str | None, email: str) -> bool:
    stmt = select(User).where(User.email == email)
    stmt = stmt.where(User.tenant_id == tenant_id) if tenant_id else stmt.where(User.tenant_id.is_(None))
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def create_user(session: AsyncSession, tenant_id: str, payload: CreateUserRequest) -> User:
    if payload.role not in TENANT_CREATABLE_ROLES:
        raise AppError(
            422, "INVALID_ROLE", "Role must be ORG_ADMIN, MODERATOR, or PARTICIPANT"
        )
    if await _email_taken(session, tenant_id, payload.email):
        raise AppError(409, "EMAIL_EXISTS", "Email already exists in this tenant")
    user = User(
        id=new_uuid(),
        tenant_id=tenant_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_super_admin(session: AsyncSession, payload: CreateSuperAdminRequest) -> User:
    if await _email_taken(session, None, payload.email):
        raise AppError(409, "EMAIL_EXISTS", "A Super Admin with this email already exists")
    user = User(
        id=new_uuid(),
        tenant_id=None,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="SUPER_ADMIN",
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def list_users(
    session: AsyncSession, tenant_id: str, *, role: str | None, status: str | None, limit: int
) -> list[User]:
    stmt = select(User).where(User.tenant_id == tenant_id)
    if role:
        stmt = stmt.where(User.role == role)
    if status:
        stmt = stmt.where(User.status == status)
    stmt = stmt.order_by(User.created_at).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_user(session: AsyncSession, tenant_id: str, user_id: str) -> User:
    user = (
        await session.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if user is None:
        raise AppError(404, "NOT_FOUND", "User not found")
    return user


async def update_user(
    session: AsyncSession, tenant_id: str, user_id: str, payload: UpdateUserRequest
) -> User:
    user = await get_user(session, tenant_id, user_id)
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.status is not None:
        if payload.status not in ("ACTIVE", "DISABLED"):
            raise AppError(422, "INVALID_STATUS", "Status must be ACTIVE or DISABLED")
        user.status = payload.status
    await session.commit()
    await session.refresh(user)
    return user


_ = ROLES  # re-exported reference for callers/tests
