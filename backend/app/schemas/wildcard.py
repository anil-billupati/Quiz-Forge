"""WildcardConfig request/response schemas (api-contracts Wildcards)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.wildcard_config import ELIGIBILITIES, WILDCARD_TYPES


class WildcardConfigCreate(BaseModel):
    type: Literal["FIFTY_FIFTY", "SECOND_CHANCE", "SKIP"]
    eligibility: Literal["ALL", "TOP_50_PERCENT"] = "ALL"


class WildcardConfigUpdate(BaseModel):
    eligibility: Literal["ALL", "TOP_50_PERCENT"] | None = None


class WildcardConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    config_block_id: str
    type: str
    eligibility: str
    created_at: datetime
    updated_at: datetime


class WildcardActivate(BaseModel):
    """Client -> server action payload for ``wildcard.activate`` (Unit 11)."""

    type: Literal["FIFTY_FIFTY", "SECOND_CHANCE", "SKIP"]
    question_id: str


class WildcardApplied(BaseModel):
    """Server -> client result of a wildcard activation (Unit 11, FR-27)."""

    event: str = "wildcard.applied"
    type: str
    question_id: str
    accepted: bool
    activation_id: str | None = None
    outcome: dict | None = None
    reason: str | None = None


class WildcardActivationAudit(BaseModel):
    """Org Admin view of a single wildcard activation (api-contracts /wildcard-audit)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    participant_id: str
    question_id: str
    type: str
    activated_at: datetime
    outcome: dict


__all__ = [
    "WildcardConfigCreate",
    "WildcardConfigUpdate",
    "WildcardConfigResponse",
    "WildcardActivate",
    "WildcardApplied",
    "WildcardActivationAudit",
    "WILDCARD_TYPES",
    "ELIGIBILITIES",
]
