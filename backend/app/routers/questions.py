"""Question & Option endpoints — Org Admin (api-contracts Questions).

Draft-only authoring. The list/get responses are the admin view and include
option correctness; participant-facing runtime payloads omit it (later units).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.schemas.question import (
    OptionSetReplace,
    QuestionBulkCreate,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
)
from app.services import question_service as svc

router = APIRouter(prefix="/contests/{contest_id}/questions", tags=["Questions"])
_org_admin = require_roles("ORG_ADMIN")


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.post("", response_model=QuestionResponse, status_code=201)
async def create_question(
    contest_id: str,
    body: QuestionCreate,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> QuestionResponse:
    tenant_id = _require_tenant(principal)
    question = await svc.create_question(session, tenant_id, contest_id, body)
    return QuestionResponse.model_validate(question)


@router.post("/bulk", response_model=list[QuestionResponse], status_code=201)
async def create_questions_bulk(
    contest_id: str,
    body: QuestionBulkCreate,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> list[QuestionResponse]:
    tenant_id = _require_tenant(principal)
    questions = await svc.create_questions_bulk(session, tenant_id, contest_id, body)
    return [QuestionResponse.model_validate(q) for q in questions]


@router.get("", response_model=list[QuestionResponse])
async def list_questions(
    contest_id: str,
    group_id: str | None = None,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> list[QuestionResponse]:
    tenant_id = _require_tenant(principal)
    questions = await svc.list_questions(session, tenant_id, contest_id, group_id)
    return [QuestionResponse.model_validate(q) for q in questions]


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    contest_id: str,
    question_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> QuestionResponse:
    tenant_id = _require_tenant(principal)
    question = await svc.get_question(session, tenant_id, contest_id, question_id)
    return QuestionResponse.model_validate(question)


@router.patch("/{question_id}", response_model=QuestionResponse)
async def update_question(
    contest_id: str,
    question_id: str,
    body: QuestionUpdate,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> QuestionResponse:
    tenant_id = _require_tenant(principal)
    question = await svc.update_question(session, tenant_id, contest_id, question_id, body)
    return QuestionResponse.model_validate(question)


@router.delete("/{question_id}", status_code=204)
async def delete_question(
    contest_id: str,
    question_id: str,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> Response:
    tenant_id = _require_tenant(principal)
    await svc.delete_question(session, tenant_id, contest_id, question_id)
    return Response(status_code=204)


@router.put("/{question_id}/options", response_model=QuestionResponse)
async def replace_options(
    contest_id: str,
    question_id: str,
    body: OptionSetReplace,
    principal: Principal = Depends(_org_admin),
    session: AsyncSession = Depends(db_session),
) -> QuestionResponse:
    tenant_id = _require_tenant(principal)
    question = await svc.replace_options(session, tenant_id, contest_id, question_id, body)
    return QuestionResponse.model_validate(question)
