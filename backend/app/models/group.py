"""Group — a sequenced sub-section of a Grouped contest (domain-model §2, FR-8).

Tenant-scoped and owned by a Contest. The table is named ``contest_group`` to
avoid the reserved SQL word ``group``. Groups are unique by run ``sequence``
within a contest. Queries are scoped to the caller's tenant in the service layer.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid


class Group(Base, TenantScoped):
    __tablename__ = "contest_group"
    __table_args__ = (
        UniqueConstraint("tenant_id", "contest_id", "sequence", name="uq_group_contest_sequence"),
        Index("ix_group_contest", "tenant_id", "contest_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str] = mapped_column(String(36), ForeignKey("contest.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    # Used by the WEIGHTED_SUM rollup strategy; null otherwise.
    weight: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
