"""Contest and its lifecycle audit (domain-model §2, FR-6/7/9, BR-5).

Contest is tenant-scoped (every contest belongs to exactly one organization).
ContestLifecycleEvent is an append-only audit of status transitions. Queries are
additionally scoped to the caller's tenant in the service layer so isolation
holds even where the session-level auto-filter is not active (tests).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid

STRUCTURES = ("NORMAL", "GROUPED")
ROLLUP_STRATEGIES = ("SUM", "WEIGHTED_SUM", "BEST_N")
LIFECYCLE_STATUSES = (
    "DRAFT",
    "PUBLISHED",
    "REGISTRATION_OPEN",
    "REGISTRATION_CLOSED",
    "SCHEDULED",
    "LIVE",
    "COMPLETED",
    "ARCHIVED",
)


class Contest(Base, TenantScoped):
    __tablename__ = "contest"
    __table_args__ = (
        Index("ix_contest_tenant_status", "tenant_id", "lifecycle_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    structure: Mapped[str] = mapped_column(String(16), nullable=False)  # NORMAL | GROUPED
    lifecycle_status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    scheduled_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    group_score_rollup: Mapped[str | None] = mapped_column(String(16), nullable=True)
    rollup_best_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ContestLifecycleEvent(Base, TenantScoped):
    """Append-only audit of contest status transitions (domain-model §2)."""

    __tablename__ = "contest_lifecycle_event"
    __table_args__ = (
        Index("ix_lifecycle_event_contest", "tenant_id", "contest_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str] = mapped_column(String(36), ForeignKey("contest.id"), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(24), nullable=False)
    new_status: Mapped[str] = mapped_column(String(24), nullable=False)
    triggered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Attribute renamed to avoid clashing with SQLAlchemy's reserved ``metadata``.
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
