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


__all__ = [
    "WildcardConfigCreate",
    "WildcardConfigUpdate",
    "WildcardConfigResponse",
    "WILDCARD_TYPES",
    "ELIGIBILITIES",
]
