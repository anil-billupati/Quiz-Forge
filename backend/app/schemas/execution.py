"""Execution-engine schemas (api-contracts §Live runtime control)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AdvanceRequest(BaseModel):
    scope: Literal["QUESTION", "GROUP"] = "QUESTION"


class ExecutionStateResponse(BaseModel):
    contest_id: str
    phase: str
    current_group_id: str | None = None
    current_question_id: str | None = None
    current_sequence: int | None = None
    submission_close_at: datetime | None = None
    version: int
    started_at: datetime | None = None
