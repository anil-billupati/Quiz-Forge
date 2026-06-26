"""EliminationRule and Checkpoint models (domain-model §2, FR-33/34/35, BR-4).

Both are children of a ConfigurationBlock and apply only when the block's
``mode`` is ELIMINATION. How a block's rules combine is decided once at the block
level (``ConfigurationBlock.elimination_combine_operator``), not per rule. A
checkpoint defines *when* the rule set is evaluated during a live contest.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid

RULE_TYPES = ("FIRST_WRONG", "N_WRONG", "BOTTOM_X_PERCENT", "MIN_SCORE")
CHECKPOINT_TYPES = ("AFTER_QUESTION", "AFTER_GROUP", "CUSTOM_MILESTONE")


class EliminationRule(Base, TenantScoped):
    __tablename__ = "elimination_rule"
    __table_args__ = (Index("ix_elimination_rule_block", "tenant_id", "config_block_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    config_block_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("configuration_block.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(24), nullable=False
    )  # FIRST_WRONG | N_WRONG | BOTTOM_X_PERCENT | MIN_SCORE
    n_value: Mapped[int | None] = mapped_column(Integer, nullable=True)  # N_WRONG
    percent_value: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )  # BOTTOM_X_PERCENT (0–100)
    min_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # MIN_SCORE
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Checkpoint(Base, TenantScoped):
    __tablename__ = "checkpoint"
    __table_args__ = (Index("ix_checkpoint_block", "tenant_id", "config_block_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    config_block_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("configuration_block.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(24), nullable=False
    )  # AFTER_QUESTION | AFTER_GROUP | CUSTOM_MILESTONE
    question_sequence: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # AFTER_QUESTION
    milestone_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # CUSTOM_MILESTONE
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
