"""Live runtime endpoints (api-contracts §Live runtime / WebSocket).

- ``POST /contests/{id}/live-ticket`` — exchange a bearer token for a single-use
  WS connection ticket.
- ``GET  /contests/{id}/live-state``  — reconnect snapshot (FR-43).
- ``WS   /contests/{id}/live``        — the live channel; authenticated by the
  ticket presented as the ``ticket.<value>`` subprotocol.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import Principal, db_session, require_roles
from app.middleware.errors import AppError
from app.middleware.tenant_context import reset_current_tenant, set_current_tenant
from app.realtime.gateway import add_presence, manager, remove_presence
from app.realtime.tickets import ticket_store
from app.schemas.answer import AnswerSubmit
from app.schemas.live import LiveStateResponse, LiveTicketResponse
from app.services import answer_service
from app.services import live_service as svc

router = APIRouter(tags=["Live"])
_member = require_roles("ORG_ADMIN", "MODERATOR", "PARTICIPANT")
settings = get_settings()
logger = structlog.get_logger("app.realtime")

# WS close codes (RFC 6455 application range).
_WS_UNAUTHORIZED = 4401


def _require_tenant(principal: Principal) -> str:
    if principal.tenant_id is None:
        raise AppError(403, "FORBIDDEN", "Operation requires a tenant-scoped user")
    return principal.tenant_id


@router.post("/contests/{contest_id}/live-ticket", response_model=LiveTicketResponse)
async def create_live_ticket(
    contest_id: str,
    principal: Principal = Depends(_member),
    session: AsyncSession = Depends(db_session),
) -> LiveTicketResponse:
    tenant_id = _require_tenant(principal)
    ticket = await svc.issue_ticket(
        session, tenant_id, contest_id, principal.user_id, principal.role
    )
    return LiveTicketResponse(ticket=ticket, expires_in=settings.live_ticket_ttl_seconds)


@router.get("/contests/{contest_id}/live-state", response_model=LiveStateResponse)
async def get_live_state(
    contest_id: str,
    principal: Principal = Depends(_member),
    session: AsyncSession = Depends(db_session),
) -> LiveStateResponse:
    tenant_id = _require_tenant(principal)
    state = await svc.get_live_state(session, tenant_id, contest_id, principal.user_id)
    return LiveStateResponse(**state)


def _extract_ticket(subprotocols: list[str]) -> str | None:
    for proto in subprotocols:
        if proto.startswith("ticket."):
            return proto[len("ticket.") :]
    return None


@router.websocket("/contests/{contest_id}/live")
async def live_channel(
    websocket: WebSocket,
    contest_id: str,
    session: AsyncSession = Depends(db_session),
) -> None:
    subprotocols = websocket.scope.get("subprotocols", [])
    ticket_value = _extract_ticket(subprotocols)
    payload = ticket_store.consume(ticket_value) if ticket_value else None

    # Reject before upgrade: missing/expired/used ticket, or wrong contest.
    if payload is None or payload.contest_id != contest_id:
        await websocket.close(code=_WS_UNAUTHORIZED)
        return

    # Echo the offered subprotocol so browsers complete the handshake.
    await websocket.accept(subprotocol=f"ticket.{ticket_value}")
    await manager.connect(contest_id, websocket)
    await add_presence(contest_id, payload.user_id)
    await websocket.send_json({"event": "connection.ready", "contest_id": contest_id})

    tenant_token = set_current_tenant(payload.tenant_id)
    try:
        while True:
            message = await websocket.receive_json()
            await _handle_action(websocket, session, payload, message)
    except WebSocketDisconnect:
        pass
    finally:
        reset_current_tenant(tenant_token)
        manager.disconnect(contest_id, websocket)
        await remove_presence(contest_id, payload.user_id)


async def _handle_action(
    websocket: WebSocket,
    session: AsyncSession,
    ticket_payload,
    message: dict,
) -> None:
    """Handle client→server actions. Unit 7 supports heartbeat; Unit 9 adds
    answer.submit; richer actions (wildcard.activate, moderator.*) arrive in
    later units.
    """
    action = message.get("action")
    if action == "ping":
        await websocket.send_json({"event": "pong"})
        return

    if action == "answer.submit":
        try:
            body = AnswerSubmit.model_validate(message)
            ack = await answer_service.submit_answer(
                session,
                ticket_payload.tenant_id,
                ticket_payload.contest_id,
                ticket_payload.user_id,
                body.question_id,
                body.selected_option_id,
                body.attempt_no,
            )
        except (ValidationError, RequestValidationError) as exc:
            ack = {
                "event": "answer.ack",
                "submission_id": None,
                "accepted": False,
                "attempt_no": message.get("attempt_no", 1),
                "reason": "validation_error",
                "details": str(exc),
            }
        except AppError as exc:
            # Validation failures surface as a rejected answer.ack so the client
            # receives a deterministic response without the connection dropping.
            ack = {
                "event": "answer.ack",
                "submission_id": None,
                "accepted": False,
                "attempt_no": message.get("attempt_no", 1),
                "reason": exc.code.lower(),
            }
        await websocket.send_json(ack)
        return

    await websocket.send_json(
        {"event": "error", "reason": "unsupported_action", "action": action}
    )
