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
from app.models.elimination import Checkpoint, EliminationRule
from app.schemas.configuration import (
    CheckpointIn,
    ConfigurationBlockCreate,
    ConfigurationBlockUpdate,
    EliminationRuleIn,
    FixedScoringConfig,
    TimeBasedScoringConfig,
)
from app.services import contest_service, group_service
from app.observability.method_logging import logged

_N_WRONG_DEFAULT = 3


@logged
def _validate_elimination(
    mode: str,
    rules: list[EliminationRuleIn] | None,
    checkpoints: list[CheckpointIn] | None,
) -> None:
    """Enforce BR-4: ELIMINATION needs ≥1 rule + ≥1 checkpoint; others forbid them."""
    if mode == "ELIMINATION":
        if not rules:
            raise AppError(
                422, "INVALID_ELIMINATION_CONFIG", "ELIMINATION mode requires at least one rule"
            )
        if not checkpoints:
            raise AppError(
                422,
                "INVALID_ELIMINATION_CONFIG",
                "ELIMINATION mode requires at least one checkpoint",
            )
        for rule in rules:
            _validate_rule(rule)
        for checkpoint in checkpoints:
            _validate_checkpoint(checkpoint)
    elif rules or checkpoints:
        raise AppError(
            422,
            "INVALID_ELIMINATION_CONFIG",
            "elimination_rules/checkpoints are only allowed on ELIMINATION blocks",
        )


def _validate_rule(rule: EliminationRuleIn) -> None:
    if rule.type == "BOTTOM_X_PERCENT" and rule.percent_value is None:
        raise AppError(422, "INVALID_RULE", "BOTTOM_X_PERCENT requires percent_value")
    if rule.type == "MIN_SCORE" and rule.min_score is None:
        raise AppError(422, "INVALID_RULE", "MIN_SCORE requires min_score")


def _validate_checkpoint(checkpoint: CheckpointIn) -> None:
    if checkpoint.type == "AFTER_QUESTION" and checkpoint.question_sequence is None:
        raise AppError(422, "INVALID_CHECKPOINT", "AFTER_QUESTION requires question_sequence")
    if checkpoint.type == "CUSTOM_MILESTONE" and checkpoint.milestone_at is None:
        raise AppError(422, "INVALID_CHECKPOINT", "CUSTOM_MILESTONE requires milestone_at")


def _make_rules(tenant_id: str, rules: list[EliminationRuleIn] | None) -> list[EliminationRule]:
    return [
        EliminationRule(
            id=new_uuid(),
            tenant_id=tenant_id,
            type=r.type,
            n_value=(r.n_value if r.n_value is not None else _N_WRONG_DEFAULT)
            if r.type == "N_WRONG"
            else None,
            percent_value=r.percent_value if r.type == "BOTTOM_X_PERCENT" else None,
            min_score=r.min_score if r.type == "MIN_SCORE" else None,
        )
        for r in (rules or [])
    ]


def _make_checkpoints(tenant_id: str, checkpoints: list[CheckpointIn] | None) -> list[Checkpoint]:
    return [
        Checkpoint(
            id=new_uuid(),
            tenant_id=tenant_id,
            type=c.type,
            question_sequence=c.question_sequence if c.type == "AFTER_QUESTION" else None,
            milestone_at=c.milestone_at if c.type == "CUSTOM_MILESTONE" else None,
        )
        for c in (checkpoints or [])
    ]


@logged
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


@logged
def _derive_scoring_model(mode: str) -> str:
    return "TIME_BASED" if mode == "SPEED" else "FIXED"


@logged
def _validate_mode_structure(contest: Contest, group_id: str | None) -> None:
    if group_id is not None and contest.structure != "GROUPED":
        raise AppError(
            409,
            "CONFLICT_NOT_GROUPED",
            "Group-scoped configuration blocks apply only to GROUPED contests",
        )


@logged
async def _require_draft_contest(
    session: AsyncSession, tenant_id: str, contest_id: str
) -> Contest:
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "DRAFT":
        raise AppError(
            409, "CONFLICT_NOT_DRAFT", "Configuration is editable only while the contest is Draft"
        )
    return contest


@logged
def _serialize_scoring_config(
    cfg: FixedScoringConfig | TimeBasedScoringConfig | None, mode: str
) -> dict[str, Any]:
    if cfg is None:
        return _default_scoring_config(mode)
    return cfg.model_dump(mode="json")


@logged
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


@logged
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
    _validate_elimination(payload.mode, payload.elimination_rules, payload.checkpoints)

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
    await session.flush()

    config = ConfigurationBlock(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=contest_id,
        group_id=None,
        **_normalize_config_create(payload),
    )
    config.elimination_rules = _make_rules(tenant_id, payload.elimination_rules)
    config.checkpoints = _make_checkpoints(tenant_id, payload.checkpoints)
    session.add(config)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(409, "CONFLICT", "Configuration block already exists") from exc
    await session.refresh(config, ["elimination_rules", "checkpoints"])
    return config


@logged
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
    _validate_elimination(payload.mode, payload.elimination_rules, payload.checkpoints)

    existing = await session.execute(
        select(ConfigurationBlock).where(
            ConfigurationBlock.tenant_id == tenant_id,
            ConfigurationBlock.group_id == group_id,
        )
    )
    for row in existing.scalars().all():
        await session.delete(row)
    await session.flush()

    config = ConfigurationBlock(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=None,
        group_id=group_id,
        **_normalize_config_create(payload),
    )
    config.elimination_rules = _make_rules(tenant_id, payload.elimination_rules)
    config.checkpoints = _make_checkpoints(tenant_id, payload.checkpoints)
    session.add(config)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(409, "CONFLICT", "Configuration block already exists") from exc
    await session.refresh(config, ["elimination_rules", "checkpoints"])
    return config


@logged
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


@logged
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


@logged
async def update_contest_block(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    payload: ConfigurationBlockUpdate,
) -> ConfigurationBlock:
    await _require_draft_contest(session, tenant_id, contest_id)
    block = await get_contest_block(session, tenant_id, contest_id)
    _apply_update(block, payload)
    _apply_children_update(block, payload)
    await session.commit()
    await session.refresh(block, ["elimination_rules", "checkpoints"])
    return block


@logged
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
    _apply_children_update(block, payload)
    await session.commit()
    await session.refresh(block, ["elimination_rules", "checkpoints"])
    return block


@logged
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


@logged
def _apply_children_update(block: ConfigurationBlock, payload: ConfigurationBlockUpdate) -> None:
    """Replace elimination rules/checkpoints on PATCH and re-assert BR-4.

    A provided (non-None) array replaces the existing set; an omitted array is
    left untouched. The resulting block must satisfy BR-4 for its effective mode.
    """
    if block.mode != "ELIMINATION":
        # Non-elimination blocks carry no rules/checkpoints.
        if payload.elimination_rules or payload.checkpoints:
            raise AppError(
                422,
                "INVALID_ELIMINATION_CONFIG",
                "elimination_rules/checkpoints are only allowed on ELIMINATION blocks",
            )
        block.elimination_rules.clear()
        block.checkpoints.clear()
        return

    if payload.elimination_rules is not None:
        for rule in payload.elimination_rules:
            _validate_rule(rule)
        block.elimination_rules[:] = _make_rules(block.tenant_id, payload.elimination_rules)
    if payload.checkpoints is not None:
        for checkpoint in payload.checkpoints:
            _validate_checkpoint(checkpoint)
        block.checkpoints[:] = _make_checkpoints(block.tenant_id, payload.checkpoints)

    if not block.elimination_rules:
        raise AppError(
            422, "INVALID_ELIMINATION_CONFIG", "ELIMINATION mode requires at least one rule"
        )
    if not block.checkpoints:
        raise AppError(
            422, "INVALID_ELIMINATION_CONFIG", "ELIMINATION mode requires at least one checkpoint"
        )
