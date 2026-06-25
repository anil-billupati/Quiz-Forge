"""Question and Option request/response schemas (api-contracts Questions).

The admin authoring view includes option correctness (``is_correct``);
participant-facing payloads at runtime omit it (handled by later units).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OptionIn(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool = False


class OptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    is_correct: bool
    ordinal: int


class QuestionCreate(BaseModel):
    group_id: str | None = None
    sequence: int = Field(ge=1)
    text: str = Field(min_length=1)
    explanation: str | None = None
    options: list[OptionIn] = Field(min_length=2)


class QuestionUpdate(BaseModel):
    group_id: str | None = None
    sequence: int | None = Field(default=None, ge=1)
    text: str | None = Field(default=None, min_length=1)
    explanation: str | None = None


class OptionSetReplace(BaseModel):
    options: list[OptionIn] = Field(min_length=2)


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    contest_id: str
    group_id: str | None
    sequence: int
    text: str
    explanation: str | None
    options: list[OptionResponse] = []
    created_at: datetime
    updated_at: datetime
