"""WildcardConfig authoring service (FR-22/26, BR-13).

Wildcard configs belong to a ConfigurationBlock and are editable only while the
parent contest is in DRAFT. Tenant isolation is enforced by loading the parent
block through the existing tenant-scoped configuration service.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.configuration_block import ConfigurationBlock
from app.models.wildcard_config import ELIGIBILITIES, WILDCARD_TYPES, WildcardConfig
from app.schemas.wildcard import WildcardConfigCreate, WildcardConfigUpdate
from app.services import configuration_service
from app.observability.method_logging import logged


@logged
async def _require_block(
    session: AsyncSession, tenant_id: str, config_block_id: str
) -> ConfigurationBlock:
    """Load a configuration block by id, enforcing tenant ownership.

    The block may be contest-scoped or group-scoped; both are loaded through the
    contest path for Draft checks.
    """
    block = (
        await session.execute(
            select(ConfigurationBlock).where(
                ConfigurationBlock.id == config_block_id,
                ConfigurationBlock.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if block is None:
        raise AppError(404, "NOT_FOUND", "Configuration block not found")

    # Enforce Draft-only editing by loading the parent contest.
    contest_id = block.contest_id
    if contest_id is None:
        # Group-scoped block: resolve contest via group service is not needed
        # because the block itself carries no contest FK. We load the group.
        from app.models.group import Group

        group = (
            await session.execute(
                select(Group).where(
                    Group.id == block.group_id, Group.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()
        if group is None:
            raise AppError(404, "NOT_FOUND", "Group not found")
        contest_id = group.contest_id

    await configuration_service._require_draft_contest(session, tenant_id, contest_id)
    return block


@logged
def _validate_type(wildcard_type: str) -> None:
    if wildcard_type not in WILDCARD_TYPES:
        raise AppError(
            422,
            "INVALID_WILDCARD_TYPE",
            "type must be FIFTY_FIFTY, SECOND_CHANCE, or SKIP",
        )


@logged
def _validate_eligibility(eligibility: str) -> None:
    if eligibility not in ELIGIBILITIES:
        raise AppError(
            422,
            "INVALID_ELIGIBILITY",
            "eligibility must be ALL or TOP_50_PERCENT",
        )


@logged
async def create_wildcard_config(
    session: AsyncSession, tenant_id: str, config_block_id: str, payload: WildcardConfigCreate
) -> WildcardConfig:
    block = await _require_block(session, tenant_id, config_block_id)
    _validate_type(payload.type)
    _validate_eligibility(payload.eligibility)

    config = WildcardConfig(
        id=new_uuid(),
        tenant_id=tenant_id,
        config_block_id=block.id,
        type=payload.type,
        eligibility=payload.eligibility,
    )
    session.add(config)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            409, "CONFLICT", "Wildcard config for this type already exists"
        ) from exc
    await session.refresh(config)
    return config


@logged
async def list_wildcard_configs(
    session: AsyncSession, tenant_id: str, config_block_id: str
) -> list[WildcardConfig]:
    await _require_block(session, tenant_id, config_block_id)
    stmt = (
        select(WildcardConfig)
        .where(
            WildcardConfig.tenant_id == tenant_id,
            WildcardConfig.config_block_id == config_block_id,
        )
        .order_by(WildcardConfig.type)
    )
    return list((await session.execute(stmt)).scalars().all())


@logged
async def get_wildcard_config(
    session: AsyncSession, tenant_id: str, config_block_id: str, wildcard_type: str
) -> WildcardConfig:
    await _require_block(session, tenant_id, config_block_id)
    _validate_type(wildcard_type)
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
        raise AppError(404, "NOT_FOUND", "Wildcard config not found")
    return config


@logged
async def update_wildcard_config(
    session: AsyncSession,
    tenant_id: str,
    config_block_id: str,
    wildcard_type: str,
    payload: WildcardConfigUpdate,
) -> WildcardConfig:
    config = await get_wildcard_config(session, tenant_id, config_block_id, wildcard_type)
    if payload.eligibility is not None:
        _validate_eligibility(payload.eligibility)
        config.eligibility = payload.eligibility
    await session.commit()
    await session.refresh(config)
    return config


@logged
async def delete_wildcard_config(
    session: AsyncSession, tenant_id: str, config_block_id: str, wildcard_type: str
) -> None:
    config = await get_wildcard_config(session, tenant_id, config_block_id, wildcard_type)
    await session.delete(config)
    await session.commit()
