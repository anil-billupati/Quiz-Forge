"""Group request/response schemas (api-contracts Groups)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contest_id: str
    name: str
    sequence: int
    weight: float | None = None


class CreateGroupRequest(BaseModel):
    name: str
    sequence: int
    weight: float | None = None


class UpdateGroupRequest(BaseModel):
    name: str | None = None
    sequence: int | None = None
    weight: float | None = None
