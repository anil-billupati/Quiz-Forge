"""Score model (Unit 10, domain-model §Live Execution & Scoring, BR-8).

The Scoring Engine writes exactly one ``Score`` per accepted ``AnswerSubmission``.
At-most-once is enforced by the unique ``(tenant_id, answer_submission_id)``
constraint: a replayed scoring command never double-scores (BR-8, FR-39).
Several columns are denormalized (``group_id``, ``question_id``, ``scoring_model``)
for audit and partition-local joins.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid

SCORING_MODELS = ("FIXED", "TIME_BASED")


class Score(Base, TenantScoped):
    __tablename__ = "score"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "answer_submission_id", name="uq_score_answer_submission"
        ),
        Index("ix_score_contest_participant", "tenant_id", "contest_id", "participant_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str] = mapped_column(String(36), ForeignKey("contest.id"), nullable=False)
    group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contest_group.id"), nullable=True
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("question.id"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_account.id"), nullable=False
    )
    answer_submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("answer_submission.id"), nullable=False
    )
    scoring_model: Mapped[str] = mapped_column(String(16), nullable=False)  # FIXED | TIME_BASED
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
