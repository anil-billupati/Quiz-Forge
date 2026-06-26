"""Registration response schema (api-contracts Registration).

Self-registration takes no body: the participant is the authenticated caller and
the contest comes from the path.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    contest_id: str
    participant_id: str
    status: str
    spectator_access: bool
    joined_at: datetime | None
    final_rank: int | None
    final_score: int | None
    registered_at: datetime
