"""User and RefreshToken models (domain-model §2, FR-4/5).

User spans both scopes: SUPER_ADMIN rows are platform-scoped (``tenant_id`` is
null); all other roles are tenant-scoped. Because of the nullable tenant_id,
User does NOT use the ``TenantScoped`` auto-filter mixin — its service layer
scopes queries to the caller's tenant explicitly (see app/services/user_service).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_uuid

ROLES = ("SUPER_ADMIN", "ORG_ADMIN", "MODERATOR", "PARTICIPANT")


class User(Base):
    __tablename__ = "user_account"
    __table_args__ = (
        # Email unique within a tenant. Platform-wide SUPER_ADMIN uniqueness is
        # enforced in the service layer (partial unique index on Postgres).
        UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organization.id"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RefreshToken(Base):
    """Hashed, rotating refresh token (BR-20). Plaintext is never stored."""

    __tablename__ = "refresh_token"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_account.id"), index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_family: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
