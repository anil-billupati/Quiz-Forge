"""Organization (tenant root) and tenant-level settings (domain-model §2).

Organization is the tenant root — it is platform-scoped (not ``TenantScoped``),
since it has no parent tenant. TenantSettings holds per-tenant resource limits
(FR-3a), one row per organization.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_uuid


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    portal_url: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    custom_domain: Mapped[str | None] = mapped_column(String(512), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    # True once the tenant has published its first contest — locks slug/portal_url (BR-19).
    has_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization.id"), primary_key=True
    )
    max_concurrent_live_contests: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_participants_per_contest: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10_000
    )
    max_questions_per_contest: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    default_negative_marking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
