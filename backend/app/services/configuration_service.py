"""ConfigurationBlock authoring service (FR-10/12, BR-3/4/6/20).

Configuration blocks are editable only while the parent contest is in DRAFT.
A Normal contest has one block at contest scope; each Group in a Grouped contest
has one block. Tenant isolation is enforced by loading the parent contest/group
through existing tenant-scoped services.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.configuration_block import (
    ELIMINATION_OPERATORS,
    MODES,
    ConfigurationBlock,
)
from app.models.contest import Contest
from app.schemas.configuration import (
    ConfigurationBlockCreate,
    ConfigurationBlockUpdate,
    FixedScoringConfig,
    TimeBasedScoringConfig,
)
from app.services import contest_service, group_service


def _default_scoring_config(mode: str) -> dict[str, Any]:
    if mode == "SPEED":
        # Sensible default bands: 0-5s=100, 6-10s=75, 11-15s=50, 16-20s=25, 20+=10.
        return TimeBasedScoringConfig(
            bands=[
                {"max_seconds": 5, "points": 100},
                {"max_seconds": 10, "points": 75},
                {"max_seconds": 15, "points": 50},
                {"max_seconds": 20, "points": 25},
                {"max_seconds": 9999, "points": 10},
            ]
        ).model_dump(mode="json")
    return FixedScoringConfig().model_dump(mode="json")


def _derive_scoring_model(mode: str) -> str:
    return "TIME_BASED" if mode == "SPEED" else "FIXED"


def _validate_mode_structure(contest: Contest, group_id: str | None) -> None:
    if group_id is not None and contest.structure != "GROUPED":
        raise AppError(
            409,
            "CONFLICT_NOT_GROUPED",
            "Group-scoped configuration blocks apply only to GROUPED contests",
        )


async def _require_draft_contest(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> Contest:
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "DRAFT":
        raise AppError(
            409, "CONFLICT_NOT_DRAFT", "Configuration is editable only while the contest is Draft"
        )
    return contest


def _serialize_scoring_config(
    cfg: FixedScoringConfig | TimeBasedScoringConfig | None, mode: str
) -> dict[str, Any]:
    if cfg is None:
        return _default_scoring_config(mode)
    return cfg.model_dump(mode="json")


def _normalize_config_create(
    payload: ConfigurationBlockCreate,
) -> dict[str, Any]:
    mode = payload.mode
    if mode not in MODES:
        raise AppError(422, "INVALID_MODE", "mode must be STANDARD, SPEED, or ELIMINATION")

    scoring_config = _serialize_scoring_config(payload.scoring_config, mode)
    scoring_model = _derive_scoring_model(mode)

    elimination_operator = None
    if mode == "ELIMINATION":
        elimination_operator = payload.elimination_combine_operator
        if elimination_operator not in ELIMINATION_OPERATORS:
            raise AppError(
                422,
                "INVALID_OPERATOR",
                "ELIMINATION mode requires elimination_combine_operator AND or OR",
            )

    return {
        "mode": mode,
        "question_duration_s": payload.question_duration_s,
        "question_interval_s": payload.question_interval_s,
        "explanation_duration_s": payload.explanation_duration_s,
        "leaderboard_duration_s": payload.leaderboard_duration_s,
        "reveal_mode": payload.reveal_mode,
        "ranking_criterion": payload.ranking_criterion,
        "tie_display": payload.tie_display,
        "leaderboard_visibility": payload.leaderboard_visibility,
        "update_frequency": payload.update_frequency,
        "survivor_score_reset": payload.survivor_score_reset,
        "elimination_combine_operator": elimination_operator,
        "scoring_model": scoring_model,
        "scoring_config": scoring_config,
    }


async def create_or_replace_contest_block(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    payload: ConfigurationBlockCreate,
) -> ConfigurationBlock:
    """Create or replace the ConfigurationBlock for a Normal contest."""
    contest = await _require_draft_contest(session, tenant_id, contest_id)
    if contest.structure != "NORMAL":
        raise AppError(
            409, "CONFLICT_NOT_NORMAL", "Contest-scoped blocks apply only to NORMAL contests"
        )

    # Delete any existing block so the replacement is idempotent.
    existing = await session.execute(
        select(ConfigurationBlock).where(
            ConfigurationBlock.tenant_id == tenant_id,
            ConfigurationBlock.contest_id == contest_id,
            ConfigurationBlock.group_id.is_(None),
        )
    )
    for row in existing.scalars().all():
        await session.delete(row)

    config = ConfigurationBlock(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=contest_id,
        group_id=None,
        **_normalize_config_create(payload),
    )
    session.add(config)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(409, "CONFLICT", "Configuration block already exists") from exc
    await session.refresh(config)
    return config


async def create_or_replace_group_block(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    group_id: str,
    payload: ConfigurationBlockCreate,
) -> ConfigurationBlock:
    """Create or replace the ConfigurationBlock for a Group."""
    await _require_draft_contest(session, tenant_id, contest_id)
    await group_service.get_group(session, tenant_id, contest_id, group_id)

    existing = await session.execute(
        select(ConfigurationBlock).where(
            ConfigurationBlock.tenant_id == tenant_id,
            ConfigurationBlock.group_id == group_id,
        )
    )
    for row in existing.scalars().all():
        await session.delete(row)

    config = ConfigurationBlock(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=None,
        group_id=group_id,
        **_normalize_config_create(payload),
    )
    session.add(config)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(409, "CONFLICT", "Configuration block already exists") from exc
    await session.refresh(config)
    return config


async def get_contest_block(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> ConfigurationBlock:
    await contest_service.get_contest(session, tenant_id, contest_id)
    block = (
        await session.execute(
            select(ConfigurationBlock).where(
                ConfigurationBlock.tenant_id == tenant_id,
                ConfigurationBlock.contest_id == contest_id,
                ConfigurationBlock.group_id.is_(None),
            )
        )
    ).scalar_one_or_none()
    if block is None:
        raise AppError(404, "NOT_FOUND", "Configuration block not found")
    return block


async def get_group_block(
    session: AsyncSession, tenant_id: str, contest_id: str, group_id: str
) -> ConfigurationBlock:
    await group_service.get_group(session, tenant_id, contest_id, group_id)
    block = (
        await session.execute(
            select(ConfigurationBlock).where(
                ConfigurationBlock.tenant_id == tenant_id,
                ConfigurationBlock.group_id == group_id,
            )
        )
    ).scalar_one_or_none()
    if block is None:
        raise AppError(404, "NOT_FOUND", "Configuration block not found")
    return block


async def update_contest_block(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    payload: ConfigurationBlockUpdate,
) -> ConfigurationBlock:
    await _require_draft_contest(session, tenant_id, contest_id)
    block = await get_contest_block(session, tenant_id, contest_id)
    _apply_update(block, payload)
    await session.commit()
    await session.refresh(block)
    return block


async def update_group_block(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    group_id: str,
    payload: ConfigurationBlockUpdate,
) -> ConfigurationBlock:
    await _require_draft_contest(session, tenant_id, contest_id)
    block = await get_group_block(session, tenant_id, contest_id, group_id)
    _apply_update(block, payload)
    await session.commit()
    await session.refresh(block)
    return block


def _apply_update(block: ConfigurationBlock, payload: ConfigurationBlockUpdate) -> None:
    mode = payload.mode or block.mode

    if payload.mode is not None and payload.mode not in MODES:
        raise AppError(422, "INVALID_MODE", "mode must be STANDARD, SPEED, or ELIMINATION")

    if payload.scoring_config is not None:
        block.scoring_config = _serialize_scoring_config(payload.scoring_config, mode)
        block.mode = mode
    elif payload.mode is not None and payload.mode != block.mode:
        # Mode changed without new scoring config -> apply defaults for new mode.
        block.scoring_config = _default_scoring_config(mode)
        block.mode = mode

    if payload.question_duration_s is not None:
        block.question_duration_s = payload.question_duration_s
    if payload.question_interval_s is not None:
        block.question_interval_s = payload.question_interval_s
    if payload.explanation_duration_s is not None:
        block.explanation_duration_s = payload.explanation_duration_s
    if payload.leaderboard_duration_s is not None:
        block.leaderboard_duration_s = payload.leaderboard_duration_s
    if payload.reveal_mode is not None:
        block.reveal_mode = payload.reveal_mode
    if payload.ranking_criterion is not None:
        block.ranking_criterion = payload.ranking_criterion
    if payload.tie_display is not None:
        block.tie_display = payload.tie_display
    if payload.leaderboard_visibility is not None:
        block.leaderboard_visibility = payload.leaderboard_visibility
    if payload.update_frequency is not None:
        block.update_frequency = payload.update_frequency
    if payload.survivor_score_reset is not None:
        block.survivor_score_reset = payload.survivor_score_reset

    if mode == "ELIMINATION":
        op = payload.elimination_combine_operator or block.elimination_combine_operator
        if op not in ELIMINATION_OPERATORS:
            raise AppError(
                422,
                "INVALID_OPERATOR",
                "ELIMINATION mode requires elimination_combine_operator AND or OR",
            )
        block.elimination_combine_operator = op
    elif payload.mode is not None and mode != "ELIMINATION":
        block.elimination_combine_operator = None
