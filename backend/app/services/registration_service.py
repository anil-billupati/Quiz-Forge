"""Registration service (FR participant workflows).

Participants self-register only while a contest is in REGISTRATION_OPEN; the
participant list is finalized at REGISTRATION_CLOSED. A participant may withdraw
their own registration before the window closes; an Org Admin may withdraw any
registration. All access is scoped to the caller's tenant (NFR-8) via the parent
contest service.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.registration import STATUSES, Registration
from app.observability.method_logging import logged
from app.services import contest_service


@logged
async def register(
    session: AsyncSession, tenant_id: str, contest_id: str, participant_id: str
) -> Registration:
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "REGISTRATION_OPEN":
        raise AppError(
            409,
            "CONFLICT_REGISTRATION_CLOSED",
            "Registration is only open while the contest is in Registration Open",
        )

    registration = Registration(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=contest_id,
        participant_id=participant_id,
        status="REGISTERED",
    )
    session.add(registration)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AppError(
            409, "CONFLICT_DUPLICATE_REGISTRATION", "Already registered for this contest"
        ) from None
    await session.refresh(registration)
    return registration


@logged
async def list_registrations(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    *,
    status: str | None,
    limit: int,
) -> list[Registration]:
    await contest_service.get_contest(session, tenant_id, contest_id)
    if status is not None and status not in STATUSES:
        raise AppError(422, "INVALID_STATUS", "Unknown registration status")
    stmt = select(Registration).where(
        Registration.tenant_id == tenant_id, Registration.contest_id == contest_id
    )
    if status is not None:
        stmt = stmt.where(Registration.status == status)
    stmt = stmt.order_by(Registration.registered_at).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


@logged
async def get_my_registration(
    session: AsyncSession, tenant_id: str, contest_id: str, participant_id: str
) -> Registration:
    registration = (
        await session.execute(
            select(Registration).where(
                Registration.tenant_id == tenant_id,
                Registration.contest_id == contest_id,
                Registration.participant_id == participant_id,
            )
        )
    ).scalar_one_or_none()
    if registration is None:
        raise AppError(404, "NOT_FOUND", "You are not registered for this contest")
    return registration


@logged
async def withdraw(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    registration_id: str,
    *,
    actor_id: str,
    actor_role: str,
) -> None:
    registration = (
        await session.execute(
            select(Registration).where(
                Registration.id == registration_id,
                Registration.contest_id == contest_id,
                Registration.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if registration is None:
        raise AppError(404, "NOT_FOUND", "Registration not found")

    if actor_role == "ORG_ADMIN":
        # Org Admins may withdraw any registration at any time.
        await session.delete(registration)
        await session.commit()
        return

    # Participants may withdraw only their own registration, and only before the
    # window closes (the list is finalized at Registration Closed).
    if registration.participant_id != actor_id:
        raise AppError(403, "FORBIDDEN", "You can only withdraw your own registration")
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "REGISTRATION_OPEN":
        raise AppError(
            409,
            "CONFLICT_REGISTRATION_CLOSED",
            "Registration cannot be withdrawn after the window closes",
        )
    await session.delete(registration)
    await session.commit()
