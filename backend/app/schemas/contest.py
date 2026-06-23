"""Contest request/response schemas (api-contracts Contests / Lifecycle)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    structure: str
    lifecycle_status: str
    scheduled_start_at: datetime | None = None
    group_score_rollup: str | None = None
    rollup_best_n: int | None = None
    created_at: datetime


class CreateContestRequest(BaseModel):
    name: str
    structure: str  # NORMAL | GROUPED — validated in the service
    description: str | None = None
    group_score_rollup: str | None = None  # SUM | WEIGHTED_SUM | BEST_N (Grouped)
    rollup_best_n: int | None = None  # required when group_score_rollup == BEST_N


class UpdateContestRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class LifecycleTransitionRequest(BaseModel):
    target_status: str
    scheduled_start_at: datetime | None = None  # required when target_status == SCHEDULED
