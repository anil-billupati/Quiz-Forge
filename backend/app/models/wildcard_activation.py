"""WildcardActivation model (Unit 11, domain-model §2, FR-22..27, BR-10/11/12/13).

Durable, at-most-once record of a participant spending a wildcard. The unique
``(tenant_id, contest_id, participant_id, type)`` constraint enforces FR-26 —
each enabled wildcard is usable **once per participant for the whole contest**
(no cooldown, no per-group carryover) — and makes a double-tap safe: a second
activation of the same type cannot create a second row. ``outcome`` captures the
type-specific effect (e.g. removed options for Fifty-Fifty) for the audit/export
(FR-27).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid

WILDCARD_TYPES = ("FIFTY_FIFTY", "SECOND_CHANCE", "SKIP")


class WildcardActivation(Base, TenantScoped):
    __tablename__ = "wildcard_activation"
    __table_args__ = (
        # FR-26: at most one activation of each type per participant per contest.
        UniqueConstraint(
            "tenant_id",
            "contest_id",
            "participant_id",
            "type",
            name="uq_wildcard_activation_once_per_contest",
        ),
        Index(
            "ix_wildcard_activation_contest", "tenant_id", "contest_id", "participant_id"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str] = mapped_column(String(36), ForeignKey("contest.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("question.id"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_account.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # FIFTY_FIFTY | SECOND_CHANCE | SKIP
    outcome: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
