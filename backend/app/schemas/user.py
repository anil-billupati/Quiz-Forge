"""User request/response schemas (api-contracts Users)."""
from __future__ import annotations

from datetime import datetime

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
