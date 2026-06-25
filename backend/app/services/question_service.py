"""Question & Option authoring service (FR authoring, BR-21).

Questions and their options are editable only while the parent contest is in
DRAFT. A Normal contest's questions carry no group; a Grouped contest's
questions must belong to one of its groups. Each question has ≥2 options with
exactly one correct (BR-21). All access is scoped to the caller's tenant (NFR-8)
via the parent contest/group services.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.errors import AppError
from app.models.base import new_uuid
from app.models.contest import Contest
from app.models.question import Option, Question
from app.observability.method_logging import logged
from app.schemas.question import (
    OptionIn,
    OptionSetReplace,
    QuestionBulkCreate,
    QuestionCreate,
    QuestionUpdate,
)
from app.services import contest_service, group_service


@logged
async def _contest_for_mutation(session: AsyncSession, tenant_id: str, contest_id: str) -> Contest:
    """Load the parent contest, enforcing DRAFT for question/option edits."""
    contest = await contest_service.get_contest(session, tenant_id, contest_id)
    if contest.lifecycle_status != "DRAFT":
        raise AppError(
            409, "CONFLICT_NOT_DRAFT", "Questions are editable only while the contest is Draft"
        )
    return contest


@logged
async def _validate_scope(
    session: AsyncSession, tenant_id: str, contest: Contest, group_id: str | None
) -> None:
    """Enforce group assignment rules: required for Grouped, forbidden for Normal."""
    if contest.structure == "GROUPED":
        if group_id is None:
            raise AppError(
                422, "INVALID_GROUP", "Questions in a GROUPED contest must belong to a group"
            )
        # Confirms the group exists within this contest + tenant (404 otherwise).
        await group_service.get_group(session, tenant_id, contest.id, group_id)
    elif group_id is not None:
        raise AppError(
            422, "INVALID_GROUP", "Questions in a NORMAL contest cannot belong to a group"
        )


def _validate_options(options: list[OptionIn]) -> None:
    # ≥2 options is enforced by the schema; here we enforce exactly one correct.
    correct = sum(1 for o in options if o.is_correct)
    if correct != 1:
        raise AppError(422, "INVALID_OPTIONS", "Exactly one option must be marked correct")


def _build_options(tenant_id: str, options: list[OptionIn]) -> list[Option]:
    return [
        Option(
            id=new_uuid(),
            tenant_id=tenant_id,
            text=o.text,
            is_correct=o.is_correct,
            ordinal=index,
        )
        for index, o in enumerate(options)
    ]


@logged
async def create_question(
    session: AsyncSession, tenant_id: str, contest_id: str, payload: QuestionCreate
) -> Question:
    contest = await _contest_for_mutation(session, tenant_id, contest_id)
    await _validate_scope(session, tenant_id, contest, payload.group_id)
    _validate_options(payload.options)

    question = Question(
        id=new_uuid(),
        tenant_id=tenant_id,
        contest_id=contest_id,
        group_id=payload.group_id,
        sequence=payload.sequence,
        text=payload.text,
        explanation=payload.explanation,
    )
    question.options = _build_options(tenant_id, payload.options)
    session.add(question)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AppError(
            409, "CONFLICT_SEQUENCE", "A question with this sequence already exists"
        ) from None
    await session.refresh(question, ["options"])
    return question


@logged
async def create_questions_bulk(
    session: AsyncSession, tenant_id: str, contest_id: str, payload: QuestionBulkCreate
) -> list[Question]:
    """Atomically create multiple questions with their options.

    All questions must be valid for the same contest scope, and no two may
    share the same sequence within the same uniqueness boundary (contest for
    Normal, group for Grouped). The whole batch commits or rolls back together.
    """
    contest = await _contest_for_mutation(session, tenant_id, contest_id)

    # Pre-validate every item before touching the database so the operation is
    # atomic and fails fast on malformed input.
    seen_sequences: set[tuple[str | None, int]] = set()
    for item in payload.questions:
        await _validate_scope(session, tenant_id, contest, item.group_id)
        _validate_options(item.options)
        key = (item.group_id, item.sequence)
        if key in seen_sequences:
            raise AppError(
                409,
                "CONFLICT_SEQUENCE",
                f"Duplicate sequence {item.sequence} in bulk request",
            )
        seen_sequences.add(key)

    questions: list[Question] = []
    for item in payload.questions:
        question = Question(
            id=new_uuid(),
            tenant_id=tenant_id,
            contest_id=contest_id,
            group_id=item.group_id,
            sequence=item.sequence,
            text=item.text,
            explanation=item.explanation,
        )
        question.options = _build_options(tenant_id, item.options)
        session.add(question)
        questions.append(question)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AppError(
            409, "CONFLICT_SEQUENCE", "A question with this sequence already exists"
        ) from None

    for question in questions:
        await session.refresh(question, ["options"])
    return questions


@logged
async def list_questions(
    session: AsyncSession, tenant_id: str, contest_id: str, group_id: str | None = None
) -> list[Question]:
    await contest_service.get_contest(session, tenant_id, contest_id)
    stmt = select(Question).where(
        Question.tenant_id == tenant_id, Question.contest_id == contest_id
    )
    if group_id is not None:
        stmt = stmt.where(Question.group_id == group_id)
    stmt = stmt.order_by(Question.sequence)
    return list((await session.execute(stmt)).scalars().all())


@logged
async def get_question(
    session: AsyncSession, tenant_id: str, contest_id: str, question_id: str
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
        raise AppError(404, "NOT_FOUND", "Question not found")
    return question


@logged
async def update_question(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    question_id: str,
    payload: QuestionUpdate,
) -> Question:
    contest = await _contest_for_mutation(session, tenant_id, contest_id)
    question = await get_question(session, tenant_id, contest_id, question_id)

    if payload.group_id is not None:
        await _validate_scope(session, tenant_id, contest, payload.group_id)
        question.group_id = payload.group_id
    if payload.sequence is not None:
        question.sequence = payload.sequence
    if payload.text is not None:
        question.text = payload.text
    if payload.explanation is not None:
        question.explanation = payload.explanation

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AppError(
            409, "CONFLICT_SEQUENCE", "A question with this sequence already exists"
        ) from None
    # Full refresh: reloads onupdate-managed columns (e.g. updated_at); options
    # stay loaded (sessions use expire_on_commit=False).
    await session.refresh(question)
    return question


@logged
async def delete_question(
    session: AsyncSession, tenant_id: str, contest_id: str, question_id: str
) -> None:
    await _contest_for_mutation(session, tenant_id, contest_id)
    question = await get_question(session, tenant_id, contest_id, question_id)
    await session.delete(question)
    await session.commit()


@logged
async def replace_options(
    session: AsyncSession,
    tenant_id: str,
    contest_id: str,
    question_id: str,
    payload: OptionSetReplace,
) -> Question:
    await _contest_for_mutation(session, tenant_id, contest_id)
    question = await get_question(session, tenant_id, contest_id, question_id)
    _validate_options(payload.options)

    # Delete the old options and flush before inserting the new set: otherwise a
    # single flush may insert new rows before deleting old ones, transiently
    # breaking the one-correct / ordinal unique indexes.
    question.options.clear()
    await session.flush()
    question.options.extend(_build_options(tenant_id, payload.options))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise AppError(409, "CONFLICT", "Invalid option set") from None
    await session.refresh(question, ["options"])
    return question
