"""User management service (FR-5, §2.5).

Org Admins create/list/manage users within their own tenant. SUPER_ADMIN is
never creatable here (use create_super_admin). All queries are explicitly scoped
to the caller's tenant because User carries a nullable tenant_id and is not
covered by the automatic scoping mixin.
"""
from __future__ import annotations

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.user import ROLES, User
from app.schemas.user import (
    BulkCreateParticipantsRequest,
    BulkCreateParticipantsResult,
    BulkParticipantResult,
    CreateSuperAdminRequest,
    CreateUserRequest,
    UpdateUserRequest,
)
from app.security.passwords import generate_one_time_password, hash_password
from app.observability.method_logging import logged

TENANT_CREATABLE_ROLES = ("ORG_ADMIN", "MODERATOR", "PARTICIPANT")


@logged
async def _email_taken(session: AsyncSession, email: str) -> bool:
    # Email is globally unique across all tenants and platform users.
    stmt = select(User).where(User.email == email)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


@logged
async def create_user(session: AsyncSession, tenant_id: str, payload: CreateUserRequest) -> User:
    if payload.role not in TENANT_CREATABLE_ROLES:
        raise AppError(
            422, "INVALID_ROLE", "Role must be ORG_ADMIN, MODERATOR, or PARTICIPANT"
        )
    if await _email_taken(session, payload.email):
        raise AppError(409, "EMAIL_EXISTS", "Email already in use")
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


@logged
async def create_super_admin(session: AsyncSession, payload: CreateSuperAdminRequest) -> User:
    if await _email_taken(session, payload.email):
        raise AppError(409, "EMAIL_EXISTS", "A user with this email already exists")
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


@logged
async def bulk_create_participants(
    session: AsyncSession, tenant_id: str, payload: BulkCreateParticipantsRequest
) -> BulkCreateParticipantsResult:
    """Bulk-create PARTICIPANT accounts from a list (F5, FR-3a).

    Partial success: malformed emails and duplicates (already in the tenant or
    repeated within the batch) are SKIPPED with a reason; valid new rows are
    CREATED with a generated one-time password returned for out-of-band
    distribution. All creates commit in a single transaction.
    """
    candidate_emails = [row.email for row in payload.participants]
    existing_rows = await session.execute(
        select(User.email).where(User.email.in_(candidate_emails))
    )
    existing: set[str] = {email for (email,) in existing_rows.all()}

    seen: set[str] = set()
    results: list[BulkParticipantResult] = []
    for row in payload.participants:
        email = row.email.strip()
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            results.append(
                BulkParticipantResult(email=row.email, status="SKIPPED", reason="invalid_email")
            )
            continue
        if email in existing or email in seen:
            results.append(
                BulkParticipantResult(email=email, status="SKIPPED", reason="duplicate_email")
            )
            continue
        seen.add(email)
        otp = generate_one_time_password()
        user = User(
            id=new_uuid(),
            tenant_id=tenant_id,
            email=email,
            password_hash=hash_password(otp),
            role="PARTICIPANT",
            first_name=row.first_name,
            last_name=row.last_name,
        )
        session.add(user)
        results.append(
            BulkParticipantResult(
                email=email, status="CREATED", user_id=user.id, one_time_password=otp
            )
        )

    await session.commit()
    created = sum(1 for r in results if r.status == "CREATED")
    return BulkCreateParticipantsResult(
        created_count=created, skipped_count=len(results) - created, results=results
    )


@logged
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


@logged
async def get_user(session: AsyncSession, tenant_id: str, user_id: str) -> User:
    user = (
        await session.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if user is None:
        raise AppError(404, "NOT_FOUND", "User not found")
    return user


@logged
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
