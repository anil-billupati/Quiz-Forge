"""Answer submission request/response schemas (api-contracts §WebSocket)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AnswerSubmit(BaseModel):
    """Client -> server action payload for answer.submit."""

    question_id: str
    selected_option_id: str
    attempt_no: int = Field(default=1, ge=1)


class AnswerAck(BaseModel):
    """Server -> client acknowledgement of an answer submission."""

    event: str = "answer.ack"
    submission_id: str
    accepted: bool
    attempt_no: int
    reason: str | None = None
