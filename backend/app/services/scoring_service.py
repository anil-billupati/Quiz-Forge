"""Scoring Engine (Unit 10, FR-12..16, BR-8/14a, ADR-002).

Authoritative, at-most-once point computation. Pure scoring functions implement
the Mode-derived models (Fixed / Time-Based with bands or linear decay) plus the
Second-Chance reduced rate and Skip floor. ``score_answer`` is the idempotent
consumer: it re-resolves tenant context from the durable ``AnswerSubmission`` row
and writes exactly one ``Score`` per submission (BR-8). Group rollup and tie-break
ordering are exposed as pure helpers over ``Score``/``AnswerSubmission`` rows for
the Leaderboard Engine (Unit 12) and results.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import reset_current_tenant, set_current_tenant
from app.models.answer import AnswerSubmission
from app.models.base import new_uuid
from app.models.configuration_block import ConfigurationBlock
from app.models.contest import Contest
from app.models.group import Group
from app.models.question import Question
from app.models.score import Score
from app.observability.method_logging import logged
from app.redis_client import stream_read
from app.services import configuration_service, contest_service

SCORING_STREAM = "engine:scoring"


def _now() -> datetime:
    return datetime.now(UTC)


# --- pure scoring functions ------------------------------------------------


def score_fixed(outcome: str, attempt_no: int, cfg: dict[str, Any]) -> int:
    """Fixed scoring (FR-13/24/25): correct=correct_points, wrong/timeout=0,
    second-chance correct=reduced rate, skip=full correct value."""
    correct_points = int(cfg.get("correct_points", 10))
    second_chance_rate = float(cfg.get("second_chance_rate", 0.5))

    if outcome == "SKIPPED":
        return correct_points  # FR-25: full correct value under Fixed.
    if outcome != "CORRECT":
        return 0  # WRONG / TIMEOUT — no negative marking (BR-14a).
    if attempt_no >= 2:
        return round(correct_points * second_chance_rate)
    return correct_points


def _band_points(response_time_ms: int, bands: list[dict[str, Any]]) -> int:
    """Lowest band whose max_seconds the response does not exceed (upper-inclusive,
    first-match-wins, FR-14). Returns 0 if it exceeds every band."""
    elapsed_s = response_time_ms / 1000.0
    for band in sorted(bands, key=lambda b: b["max_seconds"]):
        if elapsed_s <= band["max_seconds"]:
            return int(band["points"])
    return 0


def _band_floor(bands: list[dict[str, Any]]) -> int:
    """Floor score for a Speed correct answer (FR-25): the minimum points awarded
    for a correct answer, i.e. the slowest (highest max_seconds) band's points."""
    if not bands:
        return 0
    return int(max(bands, key=lambda b: b["max_seconds"])["points"])


def score_time_based(
    outcome: str, response_time_ms: int | None, attempt_no: int, cfg: dict[str, Any]
) -> int:
    """Time-Based scoring (FR-14/24/25). Bands or linear decay (mutually
    exclusive). Wrong/timeout=0; skip=floor; correct=band/decay points."""
    bands = cfg.get("bands")
    decay = cfg.get("decay")

    if outcome == "SKIPPED":
        if bands:
            return _band_floor(bands)
        if decay:
            return int(decay.get("floor", 0))
        return 0
    if outcome != "CORRECT":
        return 0  # WRONG / TIMEOUT — timeout has no floor (FR-14).

    rt = response_time_ms if response_time_ms is not None else 0
    if bands:
        return _band_points(rt, bands)
    if decay:
        max_points = int(decay.get("max_points", 0))
        floor = int(decay.get("floor", 0))
        decay_rate = float(decay.get("decay_rate", 0))
        elapsed_s = rt / 1000.0
        return max(floor, round(max_points - elapsed_s * decay_rate))
    return 0


def derive_points(block: ConfigurationBlock, submission: AnswerSubmission) -> tuple[int, str]:
    """Compute (points, scoring_model) for a submission under the active block."""
    cfg = block.scoring_config or {}
    outcome = submission.outcome or "WRONG"
    if block.scoring_model == "TIME_BASED":
        return (
            score_time_based(outcome, submission.response_time_ms, submission.attempt_no, cfg),
            "TIME_BASED",
        )
    return score_fixed(outcome, submission.attempt_no, cfg), "FIXED"


# --- idempotent consumer ---------------------------------------------------


async def _block_for_submission(
    session: AsyncSession, tenant_id: str, submission: AnswerSubmission
) -> ConfigurationBlock:
    """Resolve the active ConfigurationBlock for the submission's question scope."""
    contest = await contest_service.get_contest(session, tenant_id, submission.contest_id)
    if contest.structure == "GROUPED":
        question = (
            await session.execute(
                select(Question).where(
                    Question.tenant_id == tenant_id,
                    Question.id == submission.question_id,
                )
            )
        ).scalar_one()
        return await configuration_service.get_group_block(
            session, tenant_id, submission.contest_id, question.group_id
        )
    return await configuration_service.get_contest_block(session, tenant_id, submission.contest_id)


@logged
async def score_answer(session: AsyncSession, answer_submission_id: str) -> Score | None:
    """Score a single accepted answer idempotently (at-most-once, BR-8).

    Re-resolves tenant context from the durable AnswerSubmission row (worker
    context, technical-spec §7.1). Returns the Score (existing or newly created),
    or None if the submission is missing or not ACCEPTED.
    """
    # Load the submission without tenant scoping (worker has no request context).
    submission = (
        await session.execute(
            select(AnswerSubmission).where(AnswerSubmission.id == answer_submission_id)
        )
    ).scalar_one_or_none()
    if submission is None or submission.status != "ACCEPTED":
        return None

    tenant_id = submission.tenant_id
    token = set_current_tenant(tenant_id)
    try:
        existing = (
            await session.execute(
                select(Score).where(
                    Score.tenant_id == tenant_id,
                    Score.answer_submission_id == answer_submission_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing  # at-most-once: already scored.

        block = await _block_for_submission(session, tenant_id, submission)
        points, scoring_model = derive_points(block, submission)

        score = Score(
            id=new_uuid(),
            tenant_id=tenant_id,
            contest_id=submission.contest_id,
            group_id=block.group_id,
            question_id=submission.question_id,
            participant_id=submission.participant_id,
            answer_submission_id=submission.id,
            scoring_model=scoring_model,
            points=points,
        )
        session.add(score)
        submission.scored = True
        try:
            await session.commit()
        except IntegrityError:
            # A concurrent worker scored it first; return the existing row.
            await session.rollback()
            return (
                await session.execute(
                    select(Score).where(
                        Score.tenant_id == tenant_id,
                        Score.answer_submission_id == answer_submission_id,
                    )
                )
            ).scalar_one()
        await session.refresh(score)

        # Best-effort leaderboard refresh (Unit 12). A failure here must not break
        # the at-most-once scoring ack.
        try:
            from app.services import leaderboard_service

            await leaderboard_service.handle_score_update(session, score)
        except Exception:
            pass

        return score
    finally:
        reset_current_tenant(token)


@logged
async def consume_scoring_stream(
    session: AsyncSession, last_id: str = "0", count: int = 100, block_ms: int | None = None
) -> tuple[int, str]:
    """Read pending scoring commands and score each idempotently.

    Returns (processed_count, last_seen_id). Best-effort: if Redis is unavailable
    it returns (0, last_id) so the caller can fall back to score_unscored.
    """
    try:
        entries = await stream_read(SCORING_STREAM, last_id=last_id, count=count, block_ms=block_ms)
    except Exception:  # noqa: BLE001 — Redis transport failure is non-fatal.
        return 0, last_id

    processed = 0
    seen = last_id
    for entry_id, fields in entries:
        seen = entry_id
        submission_id = fields.get("answer_submission_id")
        if submission_id:
            await score_answer(session, submission_id)
            processed += 1
    return processed, seen


@logged
async def score_unscored(session: AsyncSession, contest_id: str | None = None) -> int:
    """Re-drive any accepted-but-unscored answers (recovery path, FR-39/42).

    Idempotent: already-scored submissions are skipped by the unique constraint.
    Returns the number of submissions scored.
    """
    stmt = select(AnswerSubmission).where(
        AnswerSubmission.status == "ACCEPTED",
        AnswerSubmission.scored.is_(False),
    )
    if contest_id is not None:
        stmt = stmt.where(AnswerSubmission.contest_id == contest_id)
    pending = (await session.execute(stmt.order_by(AnswerSubmission.created_at))).scalars().all()

    scored = 0
    for submission in pending:
        result = await score_answer(session, submission.id)
        if result is not None:
            scored += 1
    return scored


# --- rollup & tie-break helpers (pure) -------------------------------------


def participant_total(score_points: list[int]) -> int:
    """Sum a participant's points, floored at 0 (BR-14a)."""
    return max(0, sum(score_points))


def group_rollup(
    contest: Contest, group_points: dict[str, int], groups: dict[str, Group] | None = None
) -> int:
    """Roll up per-group totals to a contest score per the contest's strategy (BR-15).

    SUM (default), WEIGHTED_SUM (Group.weight), or BEST_N (Contest.rollup_best_n).
    """
    strategy = contest.group_score_rollup or "SUM"
    values = list(group_points.values())

    if strategy == "WEIGHTED_SUM" and groups is not None:
        total = 0.0
        for group_id, pts in group_points.items():
            weight = getattr(groups.get(group_id), "weight", None)
            total += pts * (float(weight) if weight is not None else 1.0)
        return max(0, round(total))
    if strategy == "BEST_N" and contest.rollup_best_n:
        best = sorted(values, reverse=True)[: contest.rollup_best_n]
        return max(0, sum(best))
    return max(0, sum(values))


def tie_break_key(submissions: list[AnswerSubmission]) -> tuple[int, int, str]:
    """Deterministic tie-break key (FR-15): (total_response_time_ms,
    wrong_count, last_correct_at_iso). Lower sorts first; ties broken by the
    earliest last-correct timestamp."""
    total_time = sum(s.response_time_ms or 0 for s in submissions)
    wrong_count = sum(1 for s in submissions if s.outcome == "WRONG")
    correct_times = [
        s.server_accepted_at for s in submissions if s.outcome == "CORRECT" and s.server_accepted_at
    ]
    last_correct = max(correct_times).isoformat() if correct_times else ""
    return total_time, wrong_count, last_correct
