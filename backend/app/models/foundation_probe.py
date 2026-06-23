"""Foundation probe model — validates the migration + tenant-scoping pipeline.

This is a deliberate scaffold table used by Unit 1 tests to prove that:
  * a migration creates a tenant-scoped table, and
  * the scoping mixin filters/stamps ``tenant_id`` and the unscoped-query
    assertion fires on a violation.

It carries no business meaning and is removed once a real tenant-scoped entity
(Unit 2) exercises the same machinery.
"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid


class FoundationProbe(Base, TenantScoped):
    __tablename__ = "_foundation_probe"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
