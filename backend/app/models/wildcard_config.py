"""WildcardConfig model (domain-model §2, FR-22/26, BR-13).

Each ConfigurationBlock can enable zero or more wildcards. A wildcard's
eligibility is evaluated at runtime against the last committed leaderboard.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid

WILDCARD_TYPES = ("FIFTY_FIFTY", "SECOND_CHANCE", "SKIP")
ELIGIBILITIES = ("ALL", "TOP_50_PERCENT")


class WildcardConfig(Base, TenantScoped):
    __tablename__ = "wildcard_config"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "config_block_id", "type", name="uq_wildcard_block_type"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    config_block_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("configuration_block.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # FIFTY_FIFTY | SECOND_CHANCE | SKIP
    eligibility: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ALL"
    )  # ALL | TOP_50_PERCENT
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
