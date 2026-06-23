"""Group authoring service (FR-8).

Groups belong to a GROUPED contest and are editable only while the contest is in
DRAFT. Sequence is unique within a contest. All access is scoped to the caller's
tenant (NFR-8) by loading the parent contest through the contest service.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.contest import Contest
from app.models.group import Group
from app.schemas.group import CreateGroupRequest, UpdateGroupRequest
from app.services import contest_service


async def _contest_for_mutation(session: AsyncSession, tenant_id: str, contest_id: str) -> Contest:
    """Load the parent contest, enforcing GROUPED + DRAFT for group edits."""
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.structure != "GROUPED":
        raise AppError(409, "CONFLICT_NOT_GROUPED", "Groups apply only to GROUPED contests")
    if contest.lifecycle_status != "DRAFT":
        raise AppError(
            409, "CONFLICT_NOT_DRAFT", "Groups are editable only while the contest is Draft"
        )
    return contest


async def create_group(
    session: AsyncSession, tenant_id: str, contest_id: str, payload: CreateGroupRequest
) -> Group:
    await _contest_for_mutation(session, tenant_id, contest_id)
    group = Group(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=contest_id,
        name=payload.name,
        sequence=payload.sequence,
        weight=payload.weight,
    )
    session.add(group)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AppError(
            409, "CONFLICT_SEQUENCE", "A group with this sequence already exists"
        ) from None
    await session.refresh(group)
    return group


async def list_groups(session: AsyncSession, tenant_id: str, contest_id: str) -> list[Group]:
    # Listing is allowed in any lifecycle stage; just confirm tenant ownership.
    await contest_service.get_contest(session, tenant_id, contest_id)
    stmt = (
        select(Group)
        .where(Group.tenant_id == tenant_id, Group.contest_id == contest_id)
        .order_by(Group.sequence)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_group(
    session: AsyncSession, tenant_id: str, contest_id: str, group_id: str
) -> Group:
    group = (
        await session.execute(
            select(Group).where(
                Group.id == group_id,
                Group.contest_id == contest_id,
                Group.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if group is None:
        raise AppError(404, "NOT_FOUND", "Group not found")
    return group


async def update_group(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    group_id: str,
    payload: UpdateGroupRequest,
) -> Group:
    await _contest_for_mutation(session, tenant_id, contest_id)
    group = await get_group(session, tenant_id, contest_id, group_id)
    if payload.name is not None:
        group.name = payload.name
    if payload.sequence is not None:
        group.sequence = payload.sequence
    if payload.weight is not None:
        group.weight = payload.weight
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AppError(
            409, "CONFLICT_SEQUENCE", "A group with this sequence already exists"
        ) from None
    await session.refresh(group)
    return group


async def delete_group(
    session: AsyncSession, tenant_id: str, contest_id: str, group_id: str
) -> None:
    await _contest_for_mutation(session, tenant_id, contest_id)
    group = await get_group(session, tenant_id, contest_id, group_id)
    await session.delete(group)
    await session.commit()
