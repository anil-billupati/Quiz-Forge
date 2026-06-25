"""Live runtime schemas (api-contracts §Live runtime / WebSocket)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LiveTicketResponse(BaseModel):
    ticket: str
    expires_in: int


class LiveStateResponse(BaseModel):
    """Reconnect snapshot (FR-43).

    Until the Execution Engine (Unit 8) lands, ``phase``/``current_question``/
    ``submission_close_at`` are placeholders; the caller's registration status and
    score are populated from their Registration.
    """

    contest_id: str
    phase: str | None = None
    current_question: dict | None = None
    submission_close_at: datetime | None = None
    status: str | None = None
    score: int | None = None
