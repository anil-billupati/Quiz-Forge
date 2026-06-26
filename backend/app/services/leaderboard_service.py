"""Leaderboard Engine (Unit 12, FR-28..32, technical-spec §2).

Computes contest/group/survivor rankings from authoritative ``Score`` and
``AnswerSubmission`` rows, caches them in Redis sorted sets, and pushes
``leaderboard.update`` events to live clients.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.answer import AnswerSubmission
from app.models.configuration_block import ConfigurationBlock
from app.models.execution import QuestionWindow
from app.models.group import Group
from app.models.registration import Registration
from app.models.score import Score
from app.models.user import User
from app.observability.method_logging import logged
from app.realtime.gateway import manager, publish_event
from app.redis_client import (
    delete_keys,
    hgetall,
    hset,
    zadd,
    zrange_withscores,
)
from app.services import configuration_service, contest_service, execution_service
from app.services.scoring_service import group_rollup

VIEWS = ("CONTEST", "GROUP", "SURVIVOR")
ALL_GROUP_ID = "_all_"
PER_ANSWER_MAX_PARTICIPANTS = 500


# -----------------------------------------------------------------------------
# internal data structure
# -----------------------------------------------------------------------------


@dataclass
class _ParticipantMetrics:
    participant_id: str
    display_name: str
    score: int = 0
    total_time_ms: int = 0
    wrong_count: int = 0
    correct_count: int = 0
    answered_count: int = 0
    last_correct_at: datetime | None = None
    status: str = "REGISTERED"
    group_points: dict[str, int] = field(default_factory=dict)

    def to_entry(self, rank: int) -> dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "display_name": self.display_name,
            "rank": rank,
            "score": self.score,
            "total_time_ms": self.total_time_ms,
            "wrong_count": self.wrong_count,
            "last_correct_at": (
                self.last_correct_at.isoformat() if self.last_correct_at else None
            ),
        }

    def sort_key(
        self,
        criterion: str,
        tie_display: str,
        questions_revealed: int,
    ) -> tuple[Any, ...]:
        """Deterministic sort key; lower tuple sorts to a better rank."""
        accuracy = (
            self.correct_count / max(1, questions_revealed)
            if questions_revealed
            else 0.0
        )
        last_correct = self.last_correct_at.isoformat() if self.last_correct_at else ""

        if criterion == "SCORE_TIME":
            if tie_display == "FASTEST":
                return (-self.score, self.total_time_ms, self.wrong_count, last_correct)
            if tie_display == "LEAST_INCORRECT":
                return (-self.score, self.wrong_count, self.total_time_ms, last_correct)
            # SHARED_RANK
            return (-self.score, self.wrong_count, last_correct)

        if criterion == "ACCURACY":
            if tie_display == "LEAST_INCORRECT":
                return (-accuracy, -self.score, self.wrong_count, self.total_time_ms)
            # FASTEST and SHARED_RANK both use total_time as the accuracy tie-break.
            return (-accuracy, -self.score, self.total_time_ms)

        # SCORE_ONLY
        if tie_display == "FASTEST":
            return (-self.score, self.total_time_ms, self.wrong_count, last_correct)
        if tie_display == "LEAST_INCORRECT":
            return (-self.score, self.wrong_count, self.total_time_ms, last_correct)
        # SHARED_RANK
        return (-self.score, self.total_time_ms, self.wrong_count, last_correct)


# -----------------------------------------------------------------------------
# Redis key helpers
# -----------------------------------------------------------------------------


def _key_namespace(
    tenant_id: str, contest_id: str, group_id: str | None, view: str
) -> str:
    group = group_id or ALL_GROUP_ID
    return f"tenant:{tenant_id}:contest:{contest_id}:group:{group}:view:{view}"


def _rank_key(namespace: str) -> str:
    return f"{namespace}:rank"


def _metrics_key(namespace: str) -> str:
    return f"{namespace}:metrics"


def _meta_key(namespace: str) -> str:
    return f"{namespace}:meta"


# -----------------------------------------------------------------------------
# pure ranking
# -----------------------------------------------------------------------------


def _assign_ranks(
    entries: list[_ParticipantMetrics],
    criterion: str,
    tie_display: str,
    questions_revealed: int,
) -> list[tuple[int, _ParticipantMetrics]]:
    """Sort entries and assign ranks according to tie_display."""
    if tie_display == "SHARED_RANK":
        sorted_entries = sorted(
            entries, key=lambda e: e.sort_key(criterion, "SHARED_RANK", questions_revealed)
        )
        ranked: list[tuple[int, _ParticipantMetrics]] = []
        prev_key: tuple[Any, ...] | None = None
        rank = 0
        for i, entry in enumerate(sorted_entries):
            sk = entry.sort_key(criterion, "SHARED_RANK", questions_revealed)
            if sk != prev_key:
                rank = i + 1
                prev_key = sk
            ranked.append((rank, entry))
        return ranked

    # FASTEST / LEAST_INCORRECT — deterministic, no shared ranks.
    sorted_entries = sorted(
        entries, key=lambda e: e.sort_key(criterion, tie_display, questions_revealed)
    )
    return [(i + 1, e) for i, e in enumerate(sorted_entries)]


# -----------------------------------------------------------------------------
# data loading
# -----------------------------------------------------------------------------


async def _active_registrations(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> dict[str, Registration]:
    rows = (
        await session.execute(
            select(Registration).where(
                Registration.tenant_id == tenant_id,
                Registration.contest_id == contest_id,
            )
        )
    ).scalars().all()
    return {r.participant_id: r for r in rows}


async def _participant_display_names(
    session: AsyncSession, participant_ids: set[str]
) -> dict[str, str]:
    if not participant_ids:
        return {}
    rows = (
        await session.execute(select(User).where(User.id.in_(participant_ids)))
    ).scalars().all()
    return {u.id: f"{u.first_name} {u.last_name}".strip() or u.email for u in rows}


async def _questions_revealed_count(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> int:
    return (
        await session.execute(
            select(func.count(QuestionWindow.id)).where(
                QuestionWindow.tenant_id == tenant_id,
                QuestionWindow.contest_id == contest_id,
                QuestionWindow.revealed_at.is_not(None),
            )
        )
    ).scalar_one()


async def _build_metrics(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    view: str,
    group_id: str | None,
    registrations: dict[str, Registration],
) -> list[_ParticipantMetrics]:
    """Aggregate Score + AnswerSubmission rows into per-participant metrics."""
    participant_ids = set(registrations)
    display_names = await _participant_display_names(session, participant_ids)

    # Load scores for the requested scope.
    score_stmt = select(Score).where(
        Score.tenant_id == tenant_id, Score.contest_id == contest_id
    )
    if view == "GROUP" and group_id is not None:
        score_stmt = score_stmt.where(Score.group_id == group_id)
    scores = (await session.execute(score_stmt)).scalars().all()

    # Load the submissions referenced by those scores to get outcome/time data.
    submission_ids = [s.answer_submission_id for s in scores]
    submissions: dict[str, AnswerSubmission] = {}
    if submission_ids:
        rows = (
            await session.execute(
                select(AnswerSubmission).where(
                    AnswerSubmission.tenant_id == tenant_id,
                    AnswerSubmission.id.in_(submission_ids),
                )
            )
        ).scalars().all()
        submissions = {s.id: s for s in rows}

    metrics: dict[str, _ParticipantMetrics] = {}
    for pid in participant_ids:
        r = registrations[pid]
        metrics[pid] = _ParticipantMetrics(
            participant_id=pid,
            display_name=display_names.get(pid, pid),
            status=r.status,
        )

    for score in scores:
        sub = submissions.get(score.answer_submission_id)
        if sub is None:
            continue
        m = metrics.get(score.participant_id)
        if m is None:
            continue
        m.score += score.points
        m.total_time_ms += sub.response_time_ms or 0
        if sub.outcome == "CORRECT":
            m.correct_count += 1
            m.answered_count += 1
            if sub.server_accepted_at is not None:
                if (
                    m.last_correct_at is None
                    or sub.server_accepted_at > m.last_correct_at
                ):
                    m.last_correct_at = sub.server_accepted_at
        elif sub.outcome == "WRONG":
            m.wrong_count += 1
            m.answered_count += 1
        elif sub.outcome in ("TIMEOUT", "SKIPPED"):
            m.answered_count += 1
        # Track group points for rollup when view == CONTEST/SURVIVOR in grouped contests.
        gkey = score.group_id or ALL_GROUP_ID
        m.group_points[gkey] = m.group_points.get(gkey, 0) + score.points

    # Apply group rollup for contest-wide views in grouped contests.
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.structure == "GROUPED" and view in ("CONTEST", "SURVIVOR"):
        groups = {
            g.id: g
            for g in (
                await session.execute(
                    select(Group).where(
                        Group.tenant_id == tenant_id, Group.contest_id == contest_id
                    )
                )
            ).scalars().all()
        }
        for m in metrics.values():
            m.score = group_rollup(contest, m.group_points, groups)

    # SURVIVOR view filters out eliminated participants.
    if view == "SURVIVOR":
        return [m for m in metrics.values() if m.status != "ELIMINATED"]

    return list(metrics.values())


async def _block_for_view(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    view: str,
    group_id: str | None,
) -> ConfigurationBlock:
    # contest_service.get_contest validates tenant/contest existence and raises 404.
    await contest_service.get_contest(session, tenant_id, contest_id)
    if view == "GROUP" and group_id is not None:
        return await configuration_service.get_group_block(
            session, tenant_id, contest_id, group_id
        )
    return await configuration_service.get_contest_block(session, tenant_id, contest_id)


# -----------------------------------------------------------------------------
# public ranking API
# -----------------------------------------------------------------------------


async def _build_ranked_metrics(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    view: str,
    group_id: str | None,
) -> tuple[ConfigurationBlock, int, list[tuple[int, _ParticipantMetrics]]]:
    """Validate inputs, aggregate metrics, assign ranks, and return everything."""
    if view not in VIEWS:
        raise AppError(422, "INVALID_VIEW", "view must be CONTEST, GROUP, or SURVIVOR")
    if view == "GROUP" and group_id is None:
        raise AppError(422, "GROUP_ID_REQUIRED", "group_id is required for GROUP view")

    block = await _block_for_view(session, tenant_id, contest_id, view, group_id)
    registrations = await _active_registrations(session, tenant_id, contest_id)
    if not registrations:
        return block, 0, []

    metrics = await _build_metrics(
        session, tenant_id, contest_id, view, group_id, registrations
    )
    questions_revealed = await _questions_revealed_count(session, tenant_id, contest_id)

    ranked = _assign_ranks(
        metrics,
        block.ranking_criterion,
        block.tie_display,
        questions_revealed,
    )
    return block, questions_revealed, ranked


@logged
async def build_leaderboard(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    view: str,
    group_id: str | None,
) -> list[dict[str, Any]]:
    """Compute a leaderboard from authoritative Postgres rows.

    Returns a list of ``LeaderboardEntry`` dicts ordered by rank.
    """
    _block, _revealed, ranked = await _build_ranked_metrics(
        session, tenant_id, contest_id, view, group_id
    )
    return [entry.to_entry(rank) for rank, entry in ranked]


# -----------------------------------------------------------------------------
# Redis cache
# -----------------------------------------------------------------------------


def _zset_score(
    metric: _ParticipantMetrics, criterion: str, questions_revealed: int
) -> float:
    if criterion == "ACCURACY":
        return -(
            metric.correct_count / max(1, questions_revealed)
        )
    return -float(metric.score)


@logged
async def write_leaderboard_to_redis(
    tenant_id: str,
    contest_id: str,
    view: str,
    group_id: str | None,
    entries: list[_ParticipantMetrics],
    block: ConfigurationBlock,
    questions_revealed: int,
) -> None:
    """Persist a leaderboard snapshot to Redis."""
    namespace = _key_namespace(tenant_id, contest_id, group_id, view)
    rank_key = _rank_key(namespace)
    metrics_key = _metrics_key(namespace)
    meta_key = _meta_key(namespace)

    # Clear old data and write fresh.
    await delete_keys(rank_key, metrics_key, meta_key)

    if not entries:
        return

    mapping: dict[str, float] = {
        e.participant_id: _zset_score(e, block.ranking_criterion, questions_revealed)
        for e in entries
    }
    await zadd(rank_key, mapping)

    ranked = _assign_ranks(
        entries, block.ranking_criterion, block.tie_display, questions_revealed
    )
    metrics_map = {
        m.participant_id: json.dumps(m.to_entry(rank))
        for rank, m in ranked
    }
    await hset(metrics_key, metrics_map)

    await hset(
        meta_key,
        {
            "criterion": block.ranking_criterion,
            "tie_display": block.tie_display,
            "visibility": block.leaderboard_visibility,
            "update_frequency": block.update_frequency,
            "generated_at": datetime.now(UTC).isoformat(),
            "participant_count": str(len(entries)),
            "group_id": group_id or ALL_GROUP_ID,
            "questions_revealed": str(questions_revealed),
        },
    )


@logged
async def read_leaderboard_from_redis(
    tenant_id: str,
    contest_id: str,
    view: str,
    group_id: str | None,
) -> list[dict[str, Any]] | None:
    """Return a cached leaderboard, or None if cache is missing."""
    namespace = _key_namespace(tenant_id, contest_id, group_id, view)
    rank_key = _rank_key(namespace)
    metrics_key = _metrics_key(namespace)

    ranked = await zrange_withscores(rank_key, 0, -1)
    if not ranked:
        return None

    metrics = await hgetall(metrics_key)
    if not metrics:
        return None

    entries: list[dict[str, Any]] = []
    for participant_id, _score in ranked:
        raw = metrics.get(participant_id)
        if raw is None:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        entries.append(entry)
    return entries


@logged
async def get_leaderboard(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    view: str,
    group_id: str | None,
) -> list[dict[str, Any]]:
    """Cache-first leaderboard read; rebuilds from Postgres if Redis is empty."""
    cached = await read_leaderboard_from_redis(tenant_id, contest_id, view, group_id)
    if cached is not None:
        return cached

    block, questions_revealed, ranked = await _build_ranked_metrics(
        session, tenant_id, contest_id, view, group_id
    )
    if ranked:
        await write_leaderboard_to_redis(
            tenant_id,
            contest_id,
            view,
            group_id,
            [m for _rank, m in ranked],
            block,
            questions_revealed,
        )
    return [entry.to_entry(rank) for rank, entry in ranked]


# -----------------------------------------------------------------------------
# push
# -----------------------------------------------------------------------------


def _full_update_payload(
    view: str, group_id: str | None, entries: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "event": "leaderboard.update",
        "view": view,
        "group_id": group_id,
        "entries": entries,
    }


@logged
async def publish_leaderboard_update(
    tenant_id: str,
    contest_id: str,
    view: str,
    group_id: str | None,
    entries: list[dict[str, Any]],
    visibility: str,
) -> None:
    """Publish a leaderboard update to live clients for this contest."""
    if visibility == "HIDDEN":
        return

    if visibility == "MASKED":
        await manager.broadcast_personalized(
            contest_id,
            lambda meta: _masked_payload(meta, entries),
        )
        return

    await publish_event(
        contest_id, _full_update_payload(view, group_id, entries)
    )


def _masked_payload(
    meta: dict[str, Any], entries: list[dict[str, Any]]
) -> dict[str, Any]:
    role = meta.get("role")
    if role in ("ORG_ADMIN", "MODERATOR"):
        return _full_update_payload("MASKED", None, entries)

    user_id = meta.get("user_id")
    mine = next((e for e in entries if e["participant_id"] == user_id), None)
    if mine is None:
        return {"event": "leaderboard.update", "view": "MASKED", "entry": None}
    return {"event": "leaderboard.update", "view": "MASKED", "entry": mine}


# -----------------------------------------------------------------------------
# hooks from scoring / execution engines
# -----------------------------------------------------------------------------


@logged
async def handle_score_update(session: AsyncSession, score: Score) -> None:
    """Best-effort leaderboard refresh after a Score is written.

    Only acts immediately when ``update_frequency == PER_ANSWER`` and the contest
    is small enough; otherwise the next advance will refresh the board.
    """
    try:
        block = await _block_for_view(
            session, score.tenant_id, score.contest_id, "CONTEST", None
        )
    except Exception:
        return

    if block.update_frequency != "PER_ANSWER":
        return

    registrations = await _active_registrations(
        session, score.tenant_id, score.contest_id
    )
    if len(registrations) > PER_ANSWER_MAX_PARTICIPANTS:
        return

    await _refresh_and_push(
        session, score.tenant_id, score.contest_id, block, visibility_override=None
    )


@logged
async def handle_advance(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    scope: str,
    now: datetime,
) -> None:
    """Refresh leaderboards when a question or group ends."""
    try:
        block = await _block_for_view(session, tenant_id, contest_id, "CONTEST", None)
    except Exception:
        return

    frequency = block.update_frequency
    if frequency == "PER_GROUP" and scope != "GROUP":
        # For grouped contests we also refresh when the group actually changes.
        state = await execution_service.get_state(session, tenant_id, contest_id)
        if state is None or state.current_group_id is None:
            return
        # We already advanced; group change already happened if scope == GROUP.
        return

    await _refresh_and_push(
        session, tenant_id, contest_id, block, visibility_override=None
    )


async def _refresh_and_push(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    block: ConfigurationBlock,
    visibility_override: str | None,
) -> None:
    """Rebuild the relevant leaderboards, write to Redis, and push updates."""
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    questions_revealed = await _questions_revealed_count(session, tenant_id, contest_id)

    views_to_refresh: list[tuple[str, str | None]] = [("CONTEST", None)]
    if contest.structure == "GROUPED":
        state = await execution_service.get_state(session, tenant_id, contest_id)
        if state is not None and state.current_group_id is not None:
            views_to_refresh.append(("GROUP", state.current_group_id))
    views_to_refresh.append(("SURVIVOR", None))

    visibility = visibility_override or block.leaderboard_visibility

    for view, group_id in views_to_refresh:
        _block, _revealed, ranked = await _build_ranked_metrics(
            session, tenant_id, contest_id, view, group_id
        )
        if ranked:
            await write_leaderboard_to_redis(
                tenant_id,
                contest_id,
                view,
                group_id,
                [m for _rank, m in ranked],
                block,
                questions_revealed,
            )
        entries = [entry.to_entry(rank) for rank, entry in ranked]
        await publish_leaderboard_update(
            tenant_id, contest_id, view, group_id, entries, visibility
        )


# -----------------------------------------------------------------------------
# visibility helpers for REST endpoint
# -----------------------------------------------------------------------------


@logged
async def check_leaderboard_visibility(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    visibility: str,
    caller_role: str,
) -> None:
    """Raise AppError if a participant is not allowed to see the leaderboard now."""
    if caller_role in ("ORG_ADMIN", "MODERATOR"):
        return

    if visibility == "HIDDEN":
        raise AppError(403, "LEADERBOARD_HIDDEN", "Leaderboard is hidden for this contest")

    if visibility == "POST_QUESTION":
        state = await execution_service.get_state(session, tenant_id, contest_id)
        if state is not None and state.phase == "SUBMISSION":
            raise AppError(
                403,
                "LEADERBOARD_NOT_VISIBLE",
                "Leaderboard is visible only after the current question closes",
            )
