"""ConfigurationBlock model (domain-model §2, FR-10/12, BR-3/4/6/20).

A ConfigurationBlock defines how a contest or group is run and scored. It is
tenant-scoped and belongs to exactly one of a Contest (Normal structure) or a
Group (Grouped structure). Scoring configuration is stored as JSONB so that
mode-specific parameters (Fixed points, Time-Based bands/decay) can evolve
without schema churn, while core dimensions (mode, durations, ranking) are
typed columns for queryability.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid

MODES = ("STANDARD", "SPEED", "ELIMINATION")
REVEAL_MODES = ("AUTOMATIC", "MODERATOR_CONTROLLED")
RANKING_CRITERIA = ("SCORE_ONLY", "SCORE_TIME", "ACCURACY")
TIE_DISPLAYS = ("SHARED_RANK", "FASTEST", "LEAST_INCORRECT")
LEADERBOARD_VISIBILITIES = ("ALWAYS", "POST_QUESTION", "HIDDEN", "MASKED")
UPDATE_FREQUENCIES = ("PER_ANSWER", "PER_QUESTION", "PER_GROUP")
ELIMINATION_OPERATORS = ("AND", "OR")


class ConfigurationBlock(Base, TenantScoped):
    __tablename__ = "configuration_block"
    __table_args__ = (
        CheckConstraint(
            "(contest_id IS NOT NULL AND group_id IS NULL) "
            "OR (contest_id IS NULL AND group_id IS NOT NULL)",
            name="ck_configuration_block_one_scope",
        ),
        CheckConstraint("question_duration_s BETWEEN 5 AND 300", name="ck_question_duration"),
        CheckConstraint("question_interval_s BETWEEN 0 AND 60", name="ck_question_interval"),
        CheckConstraint("explanation_duration_s BETWEEN 0 AND 60", name="ck_explanation_duration"),
        CheckConstraint("leaderboard_duration_s BETWEEN 0 AND 60", name="ck_leaderboard_duration"),
        Index("ix_config_block_tenant", "tenant_id"),
        Index("ix_config_block_contest", "tenant_id", "contest_id"),
        Index("ix_config_block_group", "tenant_id", "group_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contest.id"), nullable=True
    )
    group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contest_group.id"), nullable=True
    )

    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # STANDARD | SPEED | ELIMINATION
    question_duration_s: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    question_interval_s: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    explanation_duration_s: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    leaderboard_duration_s: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    reveal_mode: Mapped[str] = mapped_column(
        String(24), nullable=False, default="AUTOMATIC"
    )  # AUTOMATIC | MODERATOR_CONTROLLED
    ranking_criterion: Mapped[str] = mapped_column(
        String(16), nullable=False, default="SCORE_ONLY"
    )  # SCORE_ONLY | SCORE_TIME | ACCURACY
    tie_display: Mapped[str] = mapped_column(
        String(16), nullable=False, default="SHARED_RANK"
    )  # SHARED_RANK | FASTEST | LEAST_INCORRECT
    leaderboard_visibility: Mapped[str] = mapped_column(
        String(16), nullable=False, default="POST_QUESTION"
    )  # ALWAYS | POST_QUESTION | HIDDEN | MASKED
    update_frequency: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PER_QUESTION"
    )  # PER_ANSWER | PER_QUESTION | PER_GROUP

    # ELIMINATION mode only; null for STANDARD/SPEED.
    elimination_combine_operator: Mapped[str | None] = mapped_column(
        String(8), nullable=True
    )  # AND | OR
    survivor_score_reset: Mapped[bool] = mapped_column(nullable=False, default=False)

    # Derived from mode for queryability and audit.
    scoring_model: Mapped[str] = mapped_column(String(16), nullable=False)  # FIXED | TIME_BASED

    # Mode-specific scoring parameters (Fixed vs Time-Based bands/decay).
    scoring_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
