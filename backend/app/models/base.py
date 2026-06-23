"""Declarative base and the tenant-scoping mixin (ADR-001, technical-spec §7.1).

Every tenant-scoped table inherits :class:`TenantScoped`, which adds the
``tenant_id`` column. The session machinery in ``app.db`` uses the
:class:`TenantScoped` marker to (a) auto-stamp ``tenant_id`` on insert from the
request's tenant context and (b) filter every SELECT/UPDATE/DELETE by
``tenant_id`` — rejecting unscoped access when enforcement is enabled.
"""
from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ContestForge models."""


class TenantScoped:
    """Mixin marking a model as tenant-scoped and supplying ``tenant_id``.

    Models that belong to a single organization inherit this. Platform-scoped
    tables (e.g. the Organization root itself) do not, and are exempt from
    automatic tenant filtering.
    """

    # Stored as text to stay backend-agnostic in scaffolding; the real column
    # is a UUID FK to organization(id) once that table exists (Unit 2).
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


def new_uuid() -> str:
    """Generate a new identifier (UUIDv7-ready; v4 placeholder for scaffold)."""
    return str(uuid.uuid4())
