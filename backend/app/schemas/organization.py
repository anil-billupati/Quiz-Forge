"""Organization request/response schemas (api-contracts Organizations)."""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
_SLUG_HELP = (
    "slug must be 3-64 characters using only lowercase letters, numbers, and "
    "hyphens, and must start and end with a letter or number (e.g. 'fission-freshers')"
)


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    portal_url: str
    custom_domain: str | None = None
    status: str
    created_at: datetime


class CreateOrganizationRequest(BaseModel):
    name: str
    slug: str = Field(description=_SLUG_HELP)
    portal_url: str
    custom_domain: str | None = None
    admin_email: EmailStr
    admin_first_name: str
    admin_last_name: str
    # Project decision: the Super Admin supplies the initial Org Admin password.
    admin_password: str = Field(min_length=8)

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str) -> str:
        if not _SLUG_RE.match(value):
            raise ValueError(_SLUG_HELP)
        return value


class UpdateOrganizationRequest(BaseModel):
    name: str | None = None
    custom_domain: str | None = None


class OrganizationStatusPatch(BaseModel):
    status: str  # ACTIVE | SUSPENDED


class TenantSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_concurrent_live_contests: int
    max_participants_per_contest: int
    max_questions_per_contest: int
    default_negative_marking: bool
    updated_at: datetime


class TenantSettingsPatch(BaseModel):
    max_concurrent_live_contests: int | None = None
    max_participants_per_contest: int | None = None
    max_questions_per_contest: int | None = None
    default_negative_marking: bool | None = None


class TenantUsageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period_start: datetime
    period_end: datetime
    contests_created: int
    live_contest_peak: int
    participant_minutes: int
    questions_created: int
    answer_submissions: int
    wildcard_activations: int
    storage_bytes: int
