"""Execution Engine (FR-17..21, technical-spec §3.2, ADR-002).

Server-authoritative contest progression. All timing is computed server-side
(FR-17): each revealed question gets a durable ``QuestionWindow`` whose
``submission_close_at`` is the sole authority for answer acceptance (FR-20).
``ContestExecutionState`` is the single durable row the engine resumes from after
a restart — no in-memory progression state is trusted.

Progression is explicit so it is deterministic and testable:
- ``reveal`` opens the current question's window (DISPLAY → SUBMISSION).
- ``advance`` closes the window and moves to the next question / group / end.
- ``tick(now)`` drives **Automatic** reveal mode on the server clock; in
  **Moderator-Controlled** mode it is a no-op and a moderator calls reveal/advance.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.contest import Contest
from app.models.execution import ContestExecutionState, QuestionWindow
from app.models.group import Group
from app.models.question import Question
from app.observability.method_logging import logged
from app.realtime.gateway import publish_event
from app.services import configuration_service, contest_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# --- ordering & lookups ---------------------------------------------------


async def _ordered_questions(
    session: AsyncSession, tenant_id: str, contest: Contest
) -> list[Question]:
    """Questions in run order: by group sequence then question sequence (Grouped),
    or by question sequence (Normal)."""
    if contest.structure == "GROUPED":
        groups = (
            await session.execute(
                select(Group)
                .where(Group.tenant_id == tenant_id, Group.contest_id == contest.id)
                .order_by(Group.sequence)
            )
        ).scalars().all()
        ordered: list[Question] = []
        for group in groups:
            rows = (
                await session.execute(
                    select(Question)
                    .where(
                        Question.tenant_id == tenant_id,
                        Question.contest_id == contest.id,
                        Question.group_id == group.id,
                    )
                    .order_by(Question.sequence)
                )
            ).scalars().all()
            ordered.extend(rows)
        return ordered
    rows = (
        await session.execute(
            select(Question)
            .where(
                Question.tenant_id == tenant_id,
                Question.contest_id == contest.id,
                Question.group_id.is_(None),
            )
            .order_by(Question.sequence)
        )
    ).scalars().all()
    return list(rows)


async def _block_for(session: AsyncSession, tenant_id: str, contest: Contest, question: Question):
    if contest.structure == "GROUPED":
        return await configuration_service.get_group_block(
            session, tenant_id, contest.id, question.group_id
        )
    return await configuration_service.get_contest_block(session, tenant_id, contest.id)


async def _window_for(
    session: AsyncSession, tenant_id: str, contest_id: str, question_id: str
) -> QuestionWindow | None:
    return (
        await session.execute(
            select(QuestionWindow).where(
                QuestionWindow.tenant_id == tenant_id,
                QuestionWindow.contest_id == contest_id,
                QuestionWindow.question_id == question_id,
            )
        )
    ).scalar_one_or_none()


@logged
async def get_state(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> ContestExecutionState | None:
    return (
        await session.execute(
            select(ContestExecutionState).where(
                ContestExecutionState.tenant_id == tenant_id,
                ContestExecutionState.contest_id == contest_id,
            )
        )
    ).scalar_one_or_none()


async def _require_state(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> ContestExecutionState:
    state = await get_state(session, tenant_id, contest_id)
    if state is None:
        raise AppError(409, "CONFLICT_NOT_STARTED", "Contest execution has not started")
    return state


def _reveal_payload(question: Question, window: QuestionWindow) -> dict[str, Any]:
    return {
        "event": "question.reveal",
        "question": {
            "id": question.id,
            "sequence": question.sequence,
            "text": question.text,
            "options": [
                {"id": o.id, "text": o.text, "ordinal": o.ordinal}
                for o in sorted(question.options, key=lambda o: o.ordinal)
            ],
        },
        "submission_close_at": _aware(window.submission_close_at).isoformat(),
    }


def _progress_payload(state: ContestExecutionState) -> dict[str, Any]:
    return {
        "event": "contest.progress",
        "phase": state.phase,
        "current_group_id": state.current_group_id,
        "current_question_id": state.current_question_id,
    }


# --- engine operations ----------------------------------------------------


@logged
async def start(session: AsyncSession, tenant_id: str, contest_id: str) -> ContestExecutionState:
    """Begin execution of a Live contest (idempotent)."""
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "LIVE":
        raise AppError(409, "CONFLICT_NOT_LIVE", "Contest is not live")

    existing = await get_state(session, tenant_id, contest_id)
    if existing is not None:
        return existing

    questions = await _ordered_questions(session, tenant_id, contest)
    if not questions:
        raise AppError(409, "CONFLICT_NO_QUESTIONS", "Contest has no questions to run")

    first = questions[0]
    state = ContestExecutionState(
        contest_id=contest_id,
        tenant_id=tenant_id,
        current_group_id=first.group_id,
        current_question_id=first.id,
        phase="DISPLAY",
        version=1,
    )
    session.add(state)
    await session.commit()
    await session.refresh(state)
    await publish_event(contest_id, _progress_payload(state))
    return state


@logged
async def reveal(
    session: AsyncSession, tenant_id: str, contest_id: str, now: datetime | None = None
) -> ContestExecutionState:
    """Open the current question's window (DISPLAY → SUBMISSION)."""
    now = now or _now()
    state = await _require_state(session, tenant_id, contest_id)
    if state.phase == "ENDED":
        raise AppError(409, "CONFLICT_ENDED", "Contest execution has ended")
    if state.phase == "SUBMISSION":
        return state  # already revealed (idempotent)

    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    question = await _question(session, tenant_id, contest_id, state.current_question_id)
    block = await _block_for(session, tenant_id, contest, question)

    questions = await _ordered_questions(session, tenant_id, contest)
    run_index = _index_of(questions, question.id)

    window = await _window_for(session, tenant_id, contest_id, question.id)
    if window is None:
        window = QuestionWindow(
            id=new_uuid(),
            tenant_id=tenant_id,
            contest_id=contest_id,
            group_id=question.group_id,
            question_id=question.id,
            sequence=run_index,
            revealed_at=now,
            submission_close_at=now + timedelta(seconds=block.question_duration_s),
        )
        session.add(window)

    state.phase = "SUBMISSION"
    state.version += 1
    await session.commit()
    await session.refresh(state)
    await publish_event(contest_id, _reveal_payload(question, window))
    return state


@logged
async def advance(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    scope: str = "QUESTION",
    now: datetime | None = None,
) -> ContestExecutionState:
    """Close the current window and move to the next question / group / end."""
    now = now or _now()
    state = await _require_state(session, tenant_id, contest_id)
    if state.phase == "ENDED":
        raise AppError(409, "CONFLICT_ENDED", "Contest execution has ended")

    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    questions = await _ordered_questions(session, tenant_id, contest)

    # Close the current window so late answers are rejected (FR-20).
    if state.current_question_id is not None:
        window = await _window_for(session, tenant_id, contest_id, state.current_question_id)
        if window is not None and window.evaluated_at is None:
            window.evaluated_at = now

    current_idx = _index_of(questions, state.current_question_id)
    next_question = _next_question(questions, current_idx, scope, state.current_group_id)

    if next_question is None:
        state.phase = "ENDED"
        state.current_question_id = None
        state.version += 1
        await session.commit()
        # End of run → complete the contest lifecycle.
        await contest_service.transition_lifecycle(
            session, tenant_id, contest_id, "COMPLETED", None, None
        )
        await session.refresh(state)
        await publish_event(contest_id, _progress_payload(state))
        return state

    state.current_question_id = next_question.id
    state.current_group_id = next_question.group_id
    state.phase = "DISPLAY"
    state.version += 1
    await session.commit()
    await session.refresh(state)
    await publish_event(contest_id, _progress_payload(state))
    return state


@logged
async def tick(
    session: AsyncSession, tenant_id: str, contest_id: str, now: datetime | None = None
) -> ContestExecutionState | None:
    """Drive Automatic reveal mode on the server clock; no-op for Moderator mode."""
    now = now or _now()
    state = await get_state(session, tenant_id, contest_id)
    if state is None or state.phase == "ENDED":
        return state

    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    question = await _question(session, tenant_id, contest_id, state.current_question_id)
    block = await _block_for(session, tenant_id, contest, question)
    if block.reveal_mode != "AUTOMATIC":
        return state  # a moderator drives progression

    if state.phase == "DISPLAY":
        return await reveal(session, tenant_id, contest_id, now=now)
    if state.phase == "SUBMISSION":
        window = await _window_for(session, tenant_id, contest_id, state.current_question_id)
        if window is not None and now >= _aware(window.submission_close_at):
            return await advance(session, tenant_id, contest_id, "QUESTION", now=now)
    return state


@logged
async def snapshot(session: AsyncSession, tenant_id: str, contest_id: str) -> dict[str, Any]:
    """Describe current execution state (for control responses / live-state)."""
    state = await _require_state(session, tenant_id, contest_id)
    window = None
    if state.current_question_id is not None:
        window = await _window_for(session, tenant_id, contest_id, state.current_question_id)
    return {
        "contest_id": contest_id,
        "phase": state.phase,
        "current_group_id": state.current_group_id,
        "current_question_id": state.current_question_id,
        "current_sequence": window.sequence if window is not None else None,
        "submission_close_at": (
            _aware(window.submission_close_at)
            if window is not None and state.phase == "SUBMISSION"
            else None
        ),
        "version": state.version,
        "started_at": _aware(state.started_at) if state.started_at else None,
    }


@logged
async def current_question_view(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> dict[str, Any] | None:
    """Participant-facing current question (no correctness), when a window is open."""
    state = await get_state(session, tenant_id, contest_id)
    if state is None or state.phase != "SUBMISSION" or state.current_question_id is None:
        return None
    question = await _question(session, tenant_id, contest_id, state.current_question_id)
    return {
        "id": question.id,
        "sequence": question.sequence,
        "text": question.text,
        "options": [
            {"id": o.id, "text": o.text, "ordinal": o.ordinal}
            for o in sorted(question.options, key=lambda o: o.ordinal)
        ],
    }


# --- helpers --------------------------------------------------------------


async def _question(
    session: AsyncSession, tenant_id: str, contest_id: str, question_id: str | None
) -> Question:
    question = (
        await session.execute(
            select(Question).where(
                Question.id == question_id,
                Question.contest_id == contest_id,
                Question.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if question is None:
        raise AppError(409, "CONFLICT_NO_CURRENT_QUESTION", "No current question to reveal")
    return question


def _index_of(questions: list[Question], question_id: str | None) -> int:
    for i, q in enumerate(questions):
        if q.id == question_id:
            return i
    return -1


def _next_question(
    questions: list[Question], current_idx: int, scope: str, current_group_id: str | None
) -> Question | None:
    if current_idx < 0:
        return None
    if scope == "GROUP":
        for q in questions[current_idx + 1 :]:
            if q.group_id != current_group_id:
                return q
        return None
    return questions[current_idx + 1] if current_idx + 1 < len(questions) else None
