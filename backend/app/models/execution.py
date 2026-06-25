"""Execution-engine models (domain-model §2, FR-17..21, ADR-002).

``ContestExecutionState`` is the single durable source the engine reads on
restart to resume a Live contest without loss or double-progression (one row per
contest). ``QuestionWindow`` records the authoritative server-side timing for
each question run — ``submission_close_at`` is the sole authority for accepting or
rejecting answers (FR-20) and for recovering open windows after a crash.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid

# Per-question lifecycle (FR-18) plus grouped/terminal phases (FR-21).
PHASES = (
    "DISPLAY",
    "SUBMISSION",
    "EVALUATION",
    "EXPLANATION",
    "LEADERBOARD",
    "INTERVAL",
    "BETWEEN_GROUPS",
    "ENDED",
)


class ContestExecutionState(Base, TenantScoped):
    __tablename__ = "contest_execution_state"

    # Singleton per contest: the contest id is the primary key.
    contest_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contest.id"), primary_key=True
    )
    current_group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contest_group.id"), nullable=True
    )
    current_question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("question.id"), nullable=True
    )
    phase: Mapped[str] = mapped_column(String(16), nullable=False, default="DISPLAY")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class QuestionWindow(Base, TenantScoped):
    __tablename__ = "question_window"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "contest_id", "question_id", name="uq_question_window_contest_question"
        ),
        Index("ix_question_window_seq", "tenant_id", "contest_id", "sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contest.id"), nullable=False
    )
    group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contest_group.id"), nullable=True
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("question.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
