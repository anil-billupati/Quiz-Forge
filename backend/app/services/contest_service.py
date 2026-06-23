"""Contest authoring & lifecycle service (FR-6/7/9, BR-5).

Org Admins create and manage contests within their own tenant. The lifecycle is
a strict, non-skippable state machine; every transition is recorded in
ContestLifecycleEvent. Metadata edits and deletes are Draft-only. All queries are
explicitly scoped to the caller's tenant for isolation (NFR-8).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.contest import (
    LIFECYCLE_STATUSES,
    ROLLUP_STRATEGIES,
    STRUCTURES,
    Contest,
    ContestLifecycleEvent,
)
from app.models.organization import Organization
from app.schemas.contest import CreateContestRequest, UpdateContestRequest

# The lifecycle is a fixed, ordered sequence; a contest advances one step at a
# time and never skips (BR-5).
_LIFECYCLE_ORDER: tuple[str, ...] = LIFECYCLE_STATUSES
_NEXT_STATUS: dict[str, str] = {
    _LIFECYCLE_ORDER[i]: _LIFECYCLE_ORDER[i + 1] for i in range(len(_LIFECYCLE_ORDER) - 1)
}


def _validate_rollup(group_score_rollup: str | None, rollup_best_n: int | None) -> None:
    if group_score_rollup is None:
        return
    if group_score_rollup not in ROLLUP_STRATEGIES:
        raise AppError(
            422, "INVALID_ROLLUP", "group_score_rollup must be SUM, WEIGHTED_SUM, or BEST_N"
        )
    if group_score_rollup == "BEST_N" and rollup_best_n is None:
        raise AppError(
            422, "INVALID_ROLLUP", "rollup_best_n is required when group_score_rollup is BEST_N"
        )


async def create_contest(
    session: AsyncSession, tenant_id: str, payload: CreateContestRequest, created_by: str
) -> Contest:
    if payload.structure not in STRUCTURES:
        raise AppError(422, "INVALID_STRUCTURE", "structure must be NORMAL or GROUPED")
    _validate_rollup(payload.group_score_rollup, payload.rollup_best_n)
    contest = Contest(
        id=new_uuid(),
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        structure=payload.structure,
        lifecycle_status="DRAFT",
        group_score_rollup=payload.group_score_rollup,
        rollup_best_n=payload.rollup_best_n,
        created_by=created_by,
    )
    session.add(contest)
    await session.commit()
    await session.refresh(contest)
    return contest


async def list_contests(
    session: AsyncSession, tenant_id: str, *, status: str | None, limit: int
) -> list[Contest]:
    stmt = select(Contest).where(Contest.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(Contest.lifecycle_status == status)
    stmt = stmt.order_by(Contest.created_at).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_contest(session: AsyncSession, tenant_id: str, contest_id: str) -> Contest:
    contest = (
        await session.execute(
            select(Contest).where(Contest.id == contest_id, Contest.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if contest is None:
        raise AppError(404, "NOT_FOUND", "Contest not found")
    return contest


async def update_contest(
    session: AsyncSession, tenant_id: str, contest_id: str, payload: UpdateContestRequest
) -> Contest:
    contest = await get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "DRAFT":
        raise AppError(409, "CONFLICT_NOT_DRAFT", "Contest metadata is editable only while Draft")
    if payload.name is not None:
        contest.name = payload.name
    if payload.description is not None:
        contest.description = payload.description
    await session.commit()
    await session.refresh(contest)
    return contest


async def delete_contest(session: AsyncSession, tenant_id: str, contest_id: str) -> None:
    contest = await get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "DRAFT":
        raise AppError(409, "CONFLICT_NOT_DRAFT", "Contest can be deleted only while Draft")
    await session.delete(contest)
    await session.commit()


async def transition_lifecycle(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    target_status: str,
    scheduled_start_at: datetime | None,
    triggered_by: str | None,
) -> Contest:
    contest = await get_contest(session, tenant_id, contest_id)
    current = contest.lifecycle_status

    if target_status not in LIFECYCLE_STATUSES:
        raise AppError(422, "INVALID_STATUS", "Unknown target lifecycle status")
    if _NEXT_STATUS.get(current) != target_status:
        raise AppError(
            409,
            "CONFLICT_INVALID_TRANSITION",
            "Lifecycle advances one step at a time and cannot skip stages",
            {"current_status": current, "target_status": target_status},
        )
    if target_status == "SCHEDULED":
        if scheduled_start_at is None:
            raise AppError(409, "CONFLICT_MISSING_START", "SCHEDULED requires scheduled_start_at")
        contest.scheduled_start_at = scheduled_start_at

    # Publishing the first contest locks the tenant's slug/portal_url (BR-19).
    if target_status == "PUBLISHED":
        org = (
            await session.execute(select(Organization).where(Organization.id == tenant_id))
        ).scalar_one_or_none()
        if org is not None:
            org.has_published = True

    contest.lifecycle_status = target_status
    session.add(
        ContestLifecycleEvent(
            id=new_uuid(),
            tenant_id=tenant_id,
            contest_id=contest.id,
            previous_status=current,
            new_status=target_status,
            triggered_by=triggered_by,
        )
    )
    await session.commit()
    await session.refresh(contest)
    return contest
