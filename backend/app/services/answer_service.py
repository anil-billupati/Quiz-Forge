"""Answer submission service (Unit 9, FR-20/38-42, ADR-002).

Durable, idempotent answer intake. All validation is server-authoritative:
contest state, registration state, execution phase, question window, and option
membership. Accepted answers are persisted together with an OutboxEvent in one
transaction; a scoring command is published to Redis Streams after commit.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.answer import AnswerSubmission, OutboxEvent
from app.models.base import new_uuid
from app.models.execution import ContestExecutionState, QuestionWindow
from app.models.question import Option
from app.models.registration import Registration
from app.observability.method_logging import logged
from app.redis_client import stream_publish
from app.services import contest_service, execution_service

SCORING_STREAM = "engine:scoring"
ACTIVE_REGISTRATION_STATUSES = ("REGISTERED", "ACTIVE")


def _idempotency_hash(
    contest_id: str, question_id: str, participant_id: str, attempt_no: int
) -> str:
    """Deterministic hash used for at-most-once answer intake (FR-39)."""
    payload = f"{contest_id}|{question_id}|{participant_id}|{attempt_no}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@logged
async def _get_open_window(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> tuple[ContestExecutionState, QuestionWindow]:
    """Return the current execution state and open question window, or raise."""
    state = await execution_service.get_state(session, tenant_id, contest_id)
    if state is None:
        raise AppError(409, "CONFLICT_NOT_STARTED", "Contest execution has not started")
    if state.phase != "SUBMISSION":
        raise AppError(409, "CONFLICT_NO_OPEN_WINDOW", "No question window is currently open")

    window = (
        await session.execute(
            select(QuestionWindow).where(
                QuestionWindow.tenant_id == tenant_id,
                QuestionWindow.contest_id == contest_id,
                QuestionWindow.question_id == state.current_question_id,
            )
        )
    ).scalar_one_or_none()
    if window is None:
        raise AppError(409, "CONFLICT_NO_OPEN_WINDOW", "No question window is currently open")
    return state, window


@logged
async def _option_for_question(
    session: AsyncSession, tenant_id: str, question_id: str, option_id: str
) -> Option:
    """Return the selected option, validating it belongs to the question."""
    option = (
        await session.execute(
            select(Option).where(
                Option.tenant_id == tenant_id,
                Option.id == option_id,
                Option.question_id == question_id,
            )
        )
    ).scalar_one_or_none()
    if option is None:
        raise AppError(422, "INVALID_OPTION", "Selected option does not belong to the question")
    return option


@logged
async def _existing_submission(
    session: AsyncSession, tenant_id: str, idempotency_hash: str
) -> AnswerSubmission | None:
    return (
        await session.execute(
            select(AnswerSubmission).where(
                AnswerSubmission.tenant_id == tenant_id,
                AnswerSubmission.idempotency_hash == idempotency_hash,
            )
        )
    ).scalar_one_or_none()


def _ack_from_submission(submission: AnswerSubmission) -> dict[str, Any]:
    return {
        "event": "answer.ack",
        "submission_id": submission.id,
        "accepted": submission.status == "ACCEPTED",
        "attempt_no": submission.attempt_no,
        "reason": submission.rejection_reason,
    }


@logged
async def submit_answer(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    participant_id: str,
    question_id: str,
    selected_option_id: str,
    attempt_no: int = 1,
) -> dict[str, Any]:
    """Validate and durably record an answer submission; return the ack envelope.

    The write is idempotent: the same natural key produces the same ack without
    creating a duplicate row.
    """
    # 1. Contest must be LIVE.
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "LIVE":
        raise AppError(409, "CONFLICT_NOT_LIVE", "Contest is not live")

    # 2. Participant must have an active registration.
    registration = (
        await session.execute(
            select(Registration).where(
                Registration.tenant_id == tenant_id,
                Registration.contest_id == contest_id,
                Registration.participant_id == participant_id,
            )
        )
    ).scalar_one_or_none()
    if registration is None or registration.status not in ACTIVE_REGISTRATION_STATUSES:
        raise AppError(
            403, "NOT_REGISTERED", "An active registration is required to submit answers"
        )

    # 3. Execution state and open window.
    state, window = await _get_open_window(session, tenant_id, contest_id)

    # 4. Submission must match the currently revealed question.
    if question_id != state.current_question_id:
        raise AppError(
            422, "WRONG_QUESTION", "Submitted question does not match the current question"
        )

    # 5. Validate the selected option belongs to the question (and read correctness).
    option = await _option_for_question(session, tenant_id, question_id, selected_option_id)

    # 6. Idempotency check.
    id_hash = _idempotency_hash(contest_id, question_id, participant_id, attempt_no)
    existing = await _existing_submission(session, tenant_id, id_hash)
    if existing is not None:
        return _ack_from_submission(existing)

    # 7. Late-submission check. We record rejected attempts so retries are idempotent.
    now = _now()
    if now >= _aware(window.submission_close_at):
        submission = AnswerSubmission(
            id=new_uuid(),
            tenant_id=tenant_id,
            contest_id=contest_id,
            question_id=question_id,
            participant_id=participant_id,
            registration_id=registration.id,
            selected_option_id=selected_option_id,
            attempt_no=attempt_no,
            idempotency_hash=id_hash,
            status="REJECTED",
            rejection_reason="window_closed",
            server_accepted_at=now,
        )
        session.add(submission)
        await session.commit()
        await session.refresh(submission)
        return _ack_from_submission(submission)

    # 8. Accept the answer. Capture scoring inputs: correctness and the
    # server-measured response time from the authoritative reveal instant (FR-14).
    outcome = "CORRECT" if option.is_correct else "WRONG"
    response_time_ms = None
    if window.revealed_at is not None:
        response_time_ms = max(0, int((now - _aware(window.revealed_at)).total_seconds() * 1000))
    submission = AnswerSubmission(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=contest_id,
        question_id=question_id,
        participant_id=participant_id,
        registration_id=registration.id,
        selected_option_id=selected_option_id,
        attempt_no=attempt_no,
        idempotency_hash=id_hash,
        status="ACCEPTED",
        outcome=outcome,
        response_time_ms=response_time_ms,
        server_accepted_at=now,
    )
    outbox = OutboxEvent(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=contest_id,
        topic="answer.submitted",
        payload={
            "answer_submission_id": submission.id,
            "tenant_id": tenant_id,
            "contest_id": contest_id,
            "question_id": question_id,
            "participant_id": participant_id,
            "attempt_no": str(attempt_no),
        },
        status="PENDING",
    )
    session.add(submission)
    session.add(outbox)
    await session.commit()
    await session.refresh(submission)
    await session.refresh(outbox)

    # 9. Best-effort publish to the scoring command stream after commit.
    await _publish_scoring_command(outbox)
    await session.commit()

    return _ack_from_submission(submission)


@logged
async def _publish_scoring_command(outbox: OutboxEvent) -> None:
    """Publish a pending outbox event to Redis Streams and mark it published."""
    try:
        await stream_publish(
            SCORING_STREAM,
            {
                "type": "score_answer",
                "tenant_id": outbox.tenant_id,
                "contest_id": outbox.contest_id,
                "answer_submission_id": outbox.payload["answer_submission_id"],
                "question_id": outbox.payload["question_id"],
                "participant_id": outbox.payload["participant_id"],
                "attempt_no": outbox.payload["attempt_no"],
            },
        )
        outbox.status = "PUBLISHED"
        outbox.published_at = _now()
    except Exception:  # noqa: BLE001 — Redis failure must not fail the ack.
        outbox.status = "PENDING"


@logged
async def redrive_pending_outbox(session: AsyncSession) -> int:
    """Re-publish any pending outbox events to Redis Streams.

    Returns the number of events successfully published. Idempotent because
    scoring consumers dedupe on answer_submission_id.
    """
    pending = (
        await session.execute(
            select(OutboxEvent).where(OutboxEvent.status == "PENDING").order_by(
                OutboxEvent.created_at
            )
        )
    ).scalars().all()

    published = 0
    for outbox in pending:
        await _publish_scoring_command(outbox)
        if outbox.status == "PUBLISHED":
            published += 1

    await session.commit()
    return published
