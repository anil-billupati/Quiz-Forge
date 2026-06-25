"""Registration model (domain-model §2, FR participant workflows).

A Registration links a participant (User) to a Contest. Participants self-register
while the contest is in REGISTRATION_OPEN; the list is finalized at
REGISTRATION_CLOSED. Status advances through the live run (later units); runtime
fields (joined_at, final_rank/score, spectator_access) are set then.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid

STATUSES = ("REGISTERED", "ACTIVE", "ELIMINATED", "COMPLETED")


class Registration(Base, TenantScoped):
    __tablename__ = "registration"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "contest_id", "participant_id", name="uq_registration_contest_participant"
        ),
        Index("ix_registration_contest_status", "tenant_id", "contest_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contest.id"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_account.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="REGISTERED")
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    spectator_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    final_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
