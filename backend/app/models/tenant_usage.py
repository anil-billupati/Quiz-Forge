"""TenantUsageRecord — periodic per-tenant usage aggregate (FR-3b).

Foundation for capacity planning / future billing. Unit 2 creates the table and
the read endpoint; later units increment the counters as events occur.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_uuid


class TenantUsageRecord(Base):
    __tablename__ = "tenant_usage_record"
    __table_args__ = (
        UniqueConstraint("tenant_id", "period_start", name="uq_usage_tenant_period"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("organization.id"), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contests_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    live_contest_peak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    participant_minutes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    questions_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answer_submissions: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    wildcard_activations: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
