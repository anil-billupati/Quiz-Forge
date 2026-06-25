"""Live runtime service (Unit 7): connection tickets + reconnect snapshot.

Issues single-use WebSocket tickets after validating tenant, role, and (for
participants) an active Registration, and serves the ``/live-state`` reconnect
snapshot. The live execution detail (current question, phase, authoritative
submission window) arrives with the Execution Engine (Unit 8).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.registration import Registration
from app.observability.method_logging import logged
from app.realtime.tickets import TicketPayload, ticket_store
from app.services import contest_service, execution_service

# Statuses that permit joining the live channel.
_ACTIVE_REGISTRATION = ("REGISTERED", "ACTIVE")


@logged
async def issue_ticket(
    session: AsyncSession, tenant_id: str, contest_id: str, user_id: str, role: str
) -> str:
    """Validate the caller and mint a single-use connection ticket."""
    # 404 if the contest is not in the caller's tenant (blocks cross-tenant).
    await contest_service.get_contest(session, tenant_id, contest_id)

    if role == "PARTICIPANT":
        registration = await _get_registration(session, tenant_id, contest_id, user_id)
        if registration is None or registration.status not in _ACTIVE_REGISTRATION:
            raise AppError(
                403, "NOT_REGISTERED", "An active registration is required to join this contest"
            )

    return ticket_store.issue(
        TicketPayload(user_id=user_id, role=role, tenant_id=tenant_id, contest_id=contest_id)
    )


@logged
async def get_live_state(
    session: AsyncSession, tenant_id: str, contest_id: str, user_id: str
) -> dict[str, Any]:
    """Return the reconnect snapshot; 409 if the contest is not Live (FR-43)."""
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "LIVE":
        raise AppError(409, "CONFLICT_NOT_LIVE", "Contest is not live")

    registration = await _get_registration(session, tenant_id, contest_id, user_id)

    # Execution-engine view (Unit 8): phase, open window, current question.
    phase: str | None = None
    submission_close_at = None
    current_question = None
    state = await execution_service.get_state(session, tenant_id, contest_id)
    if state is not None:
        snap = await execution_service.snapshot(session, tenant_id, contest_id)
        phase = snap["phase"]
        submission_close_at = snap["submission_close_at"]
        current_question = await execution_service.current_question_view(
            session, tenant_id, contest_id
        )

    return {
        "contest_id": contest_id,
        "phase": phase,
        "current_question": current_question,
        "submission_close_at": submission_close_at,
        "status": registration.status if registration else None,
        "score": registration.final_score if registration else None,
    }


async def _get_registration(
    session: AsyncSession, tenant_id: str, contest_id: str, user_id: str
) -> Registration | None:
    return (
        await session.execute(
            select(Registration).where(
                Registration.tenant_id == tenant_id,
                Registration.contest_id == contest_id,
                Registration.participant_id == user_id,
            )
        )
    ).scalar_one_or_none()
