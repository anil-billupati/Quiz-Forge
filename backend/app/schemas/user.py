"""User request/response schemas (api-contracts Users)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str | None
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    status: str
    created_at: datetime


class CreateUserRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str  # validated against ORG_ADMIN | MODERATOR | PARTICIPANT in the service
    # Per project decision: the creating Org Admin supplies the password.
    password: str = Field(min_length=8)


class CreateSuperAdminRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str = Field(min_length=8)


class UpdateUserRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    status: str | None = None  # ACTIVE | DISABLED


# ── Bulk participant import (F5 / FR-3a) ─────────────────────────────────────
# `email` is a plain str (not EmailStr) so a malformed address yields a per-row
# SKIPPED result rather than failing the whole request — partial-success import.


class BulkParticipantRow(BaseModel):
    email: str
    first_name: str
    last_name: str


class BulkCreateParticipantsRequest(BaseModel):
    participants: list[BulkParticipantRow] = Field(min_length=1, max_length=5000)


class BulkParticipantResult(BaseModel):
    email: str
    status: Literal["CREATED", "SKIPPED"]
    reason: str | None = None  # e.g. duplicate_email | invalid_email (when SKIPPED)
    user_id: str | None = None  # set when CREATED
    one_time_password: str | None = None  # CREATED only; for out-of-band distribution


class BulkCreateParticipantsResult(BaseModel):
    created_count: int
    skipped_count: int
    results: list[BulkParticipantResult]
