"""Wildcard runtime (Unit 11, FR-22..27, BR-10/11/12/13).

Live activation of the three wildcards over the WS ``wildcard.activate`` action.
``activate_wildcard`` is the single entry point: it validates the contest/window/
registration, the enabled set, and eligibility, applies the type-specific effect,
and writes a durable, at-most-once ``WildcardActivation`` (FR-26 / FR-27).

Effects:
- **Fifty-Fifty** (BR-11): rejected once an answer is selected; the server removes
  two incorrect options and always preserves the correct one.
- **Second Chance** (BR-10): allowed only after a WRONG first attempt; it records
  the activation that unlocks ``attempt_no=2`` (the reduced rate is applied by the
  Scoring Engine, Unit 10).
- **Skip** (BR-12): records a durable SKIPPED answer so the Scoring Engine awards
  the full (Fixed) / floor (Speed) value without an attempt.

Eligibility ``TOP_50_PERCENT`` is evaluated against the committed leaderboard
(derived here from authoritative ``Score`` rows, BR-18) at activation time. The
Leaderboard Engine (Unit 12) can later supply this directly without changing the
contract.
"""
from __future__ import annotations

import math
import random
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.answer import AnswerSubmission
from app.models.base import new_uuid
from app.models.question import Option
from app.models.registration import Registration
from app.models.score import Score
from app.models.wildcard_activation import WILDCARD_TYPES, WildcardActivation
from app.models.wildcard_config import WildcardConfig
from app.observability.method_logging import logged
from app.services import answer_service, configuration_service, contest_service, execution_service

ACTIVE_REGISTRATION_STATUSES = ("REGISTERED", "ACTIVE")


# --- pure helpers ----------------------------------------------------------


def pick_fifty_fifty(options: list[Option], rng: random.Random | None = None) -> list[str]:
    """Pick up to two incorrect option ids to remove, preserving the correct one
    (FR-23/BR-11). Fewer than two are removed only if fewer incorrect options exist."""
    incorrect = [o.id for o in options if not o.is_correct]
    if len(incorrect) <= 2:
        return list(incorrect)
    chooser = rng or random
    return chooser.sample(incorrect, 2)


def is_top_half(participant_id: str, totals: dict[str, int]) -> bool:
    """TOP_50_PERCENT membership over committed score totals (FR-26).

    The participant is ranked by score (desc); ties share a rank and are never
    split, so a tie straddling the cut-off is included. An empty board (no
    committed scores yet) makes everyone eligible.
    """
    board = dict(totals)
    board.setdefault(participant_id, 0)
    n = len(board)
    if n <= 1:
        return True
    my = board[participant_id]
    rank = sum(1 for v in board.values() if v > my) + 1
    return rank <= math.ceil(n / 2)


# --- lookups ---------------------------------------------------------------


async def _active_registration(
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
    if registration is None or registration.status not in ACTIVE_REGISTRATION_STATUSES:
        raise AppError(
            403, "NOT_REGISTERED", "An active registration is required to use a wildcard"
        )
    return registration


async def _block_for_question(
    session: AsyncSession, tenant_id: str, contest_id: str, question
) -> Any:
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.structure == "GROUPED":
        return await configuration_service.get_group_block(
            session, tenant_id, contest_id, question.group_id
        )
    return await configuration_service.get_contest_block(session, tenant_id, contest_id)


async def _enabled_wildcard(
    session: AsyncSession, tenant_id: str, config_block_id: str, wildcard_type: str
) -> WildcardConfig:
    config = (
        await session.execute(
            select(WildcardConfig).where(
                WildcardConfig.tenant_id == tenant_id,
                WildcardConfig.config_block_id == config_block_id,
                WildcardConfig.type == wildcard_type,
            )
        )
    ).scalar_one_or_none()
    if config is None:
        raise AppError(
            409, "WILDCARD_NOT_ENABLED", "This wildcard is not enabled for the current question"
        )
    return config


async def _accepted_submissions(
    session: AsyncSession, tenant_id: str, contest_id: str, participant_id: str, question_id: str
) -> list[AnswerSubmission]:
    return list(
        (
            await session.execute(
                select(AnswerSubmission).where(
                    AnswerSubmission.tenant_id == tenant_id,
                    AnswerSubmission.contest_id == contest_id,
                    AnswerSubmission.participant_id == participant_id,
                    AnswerSubmission.question_id == question_id,
                    AnswerSubmission.status == "ACCEPTED",
                )
            )
        ).scalars().all()
    )


async def _score_totals(session: AsyncSession, tenant_id: str, contest_id: str) -> dict[str, int]:
    rows = (
        await session.execute(
            select(Score.participant_id, func.sum(Score.points))
            .where(Score.tenant_id == tenant_id, Score.contest_id == contest_id)
            .group_by(Score.participant_id)
        )
    ).all()
    return {pid: int(total or 0) for pid, total in rows}


async def _existing_activation(
    session: AsyncSession, tenant_id: str, contest_id: str, participant_id: str, wildcard_type: str
) -> WildcardActivation | None:
    return (
        await session.execute(
            select(WildcardActivation).where(
                WildcardActivation.tenant_id == tenant_id,
                WildcardActivation.contest_id == contest_id,
                WildcardActivation.participant_id == participant_id,
                WildcardActivation.type == wildcard_type,
            )
        )
    ).scalar_one_or_none()


@logged
async def list_activations_for_contest(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> list[WildcardActivation]:
    """Return all wildcard activations for a contest, ordered by activation time.

    Used by the Org Admin ``/contests/{id}/wildcard-audit`` endpoint (FR-27).
    """
    return list(
        (
            await session.execute(
                select(WildcardActivation)
                .where(
                    WildcardActivation.tenant_id == tenant_id,
                    WildcardActivation.contest_id == contest_id,
                )
                .order_by(WildcardActivation.activated_at)
            )
        )
        .scalars()
        .all()
    )


def _applied(activation: WildcardActivation) -> dict[str, Any]:
    return {
        "event": "wildcard.applied",
        "type": activation.type,
        "question_id": activation.question_id,
        "accepted": True,
        "activation_id": activation.id,
        "outcome": activation.outcome,
        "reason": None,
    }


# --- entry point -----------------------------------------------------------


@logged
async def activate_wildcard(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    participant_id: str,
    question_id: str,
    wildcard_type: str,
) -> dict[str, Any]:
    """Validate and apply a wildcard activation; return the ``wildcard.applied``
    envelope. Raises ``AppError`` for any rejection (the WS layer maps it to a
    rejected envelope)."""
    if wildcard_type not in WILDCARD_TYPES:
        raise AppError(422, "INVALID_WILDCARD_TYPE", "Unknown wildcard type")

    # 1. Contest must be LIVE.
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "LIVE":
        raise AppError(409, "CONFLICT_NOT_LIVE", "Contest is not live")

    # 2. Participant must hold an active (non-eliminated) registration.
    registration = await _active_registration(session, tenant_id, contest_id, participant_id)

    # 3. The wildcard targets the currently open question window.
    state = await execution_service.get_state(session, tenant_id, contest_id)
    if state is None or state.phase != "SUBMISSION":
        raise AppError(409, "CONFLICT_NO_OPEN_WINDOW", "No question window is currently open")
    if question_id != state.current_question_id:
        raise AppError(422, "WRONG_QUESTION", "Wildcard target is not the current question")

    question = await execution_service._question(session, tenant_id, contest_id, question_id)

    # 4. The wildcard must be enabled in the active block, and the participant must
    # be eligible (ALL, or TOP_50_PERCENT of the committed leaderboard).
    block = await _block_for_question(session, tenant_id, contest_id, question)
    config = await _enabled_wildcard(session, tenant_id, block.id, wildcard_type)
    if config.eligibility == "TOP_50_PERCENT":
        totals = await _score_totals(session, tenant_id, contest_id)
        if not is_top_half(participant_id, totals):
            raise AppError(403, "WILDCARD_NOT_ELIGIBLE", "Not eligible for this wildcard")

    # 5. At-most-once per contest (FR-26). A repeat on the same question is an
    # idempotent double-tap; on a different question it is genuinely spent.
    existing = await _existing_activation(
        session, tenant_id, contest_id, participant_id, wildcard_type
    )
    if existing is not None:
        if existing.question_id == question_id:
            return _applied(existing)
        raise AppError(409, "WILDCARD_ALREADY_USED", "This wildcard has already been used")

    # 6. Apply the type-specific effect.
    outcome = await _apply_effect(
        session, tenant_id, contest_id, participant_id, question, wildcard_type, registration
    )

    # 7. Durable, at-most-once activation log.
    activation = WildcardActivation(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=contest_id,
        question_id=question_id,
        participant_id=participant_id,
        type=wildcard_type,
        outcome=outcome,
    )
    session.add(activation)
    try:
        await session.commit()
    except IntegrityError:
        # Concurrent double-tap: another activation won; return it idempotently.
        await session.rollback()
        won = await _existing_activation(
            session, tenant_id, contest_id, participant_id, wildcard_type
        )
        if won is not None:
            return _applied(won)
        raise
    await session.refresh(activation)
    return _applied(activation)


@logged
async def _apply_effect(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    participant_id: str,
    question,
    wildcard_type: str,
    registration: Registration,
) -> dict[str, Any]:
    submissions = await _accepted_submissions(
        session, tenant_id, contest_id, participant_id, question.id
    )

    if wildcard_type == "FIFTY_FIFTY":
        if submissions:
            raise AppError(
                409, "ANSWER_ALREADY_SELECTED", "Fifty-Fifty cannot be used after answering"
            )
        removed = pick_fifty_fifty(list(question.options))
        return {"removed_options": removed}

    if wildcard_type == "SECOND_CHANCE":
        first = next((s for s in submissions if s.attempt_no == 1), None)
        if first is None:
            raise AppError(
                409, "NO_FIRST_ATTEMPT", "Second Chance requires a first attempt first"
            )
        if first.outcome != "WRONG":
            raise AppError(
                409, "NOT_WRONG_ANSWER", "Second Chance is only available after a wrong answer"
            )
        return {"attempt_no": 2, "points_effect": "reduced"}

    # SKIP — award full/floor without attempting (BR-12).
    if submissions:
        raise AppError(409, "ANSWER_ALREADY_SELECTED", "Skip cannot be used after answering")
    skip = await answer_service.record_skip_submission(
        session, tenant_id, contest_id, participant_id, question.id, registration.id
    )
    return {"skipped": True, "answer_submission_id": skip.id}
