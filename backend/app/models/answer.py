"""Answer submission and transactional outbox models (Unit 9).

Every accepted answer attempt is durably recorded in ``AnswerSubmission`` with a
deterministic ``idempotency_hash`` so retries are idempotent (FR-39). Rejected
attempts (e.g. past the server-side window) are also recorded so the same
idempotent ack is returned on retry.

``OutboxEvent`` implements the transactional outbox pattern (ADR-002): the answer
row and the outbox row are written in the same DB transaction; a best-effort
Redis Streams publish happens after commit. Pending outbox rows are re-driven on
recovery.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, new_uuid

SUBMISSION_STATUSES = ("ACCEPTED", "REJECTED")
OUTBOX_STATUSES = ("PENDING", "PUBLISHED", "FAILED")


class AnswerSubmission(Base, TenantScoped):
    """Durable record of an answer submission attempt."""

    __tablename__ = "answer_submission"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_hash", name="uq_answer_submission_idempotency"
        ),
        UniqueConstraint(
            "tenant_id",
            "contest_id",
            "question_id",
            "participant_id",
            "attempt_no",
            name="uq_answer_submission_natural_key",
        ),
        Index("ix_answer_submission_contest_status", "tenant_id", "contest_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str] = mapped_column(String(36), ForeignKey("contest.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("question.id"), nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_account.id"), nullable=False
    )
    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registration.id"), nullable=False
    )
    selected_option_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("option.id"), nullable=False
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ACCEPTED | REJECTED
    rejection_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    server_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base, TenantScoped):
    """Transactional outbox row for downstream engine commands (ADR-002)."""

    __tablename__ = "outbox_event"
    __table_args__ = (
        Index("ix_outbox_event_status_created", "status", "created_at"),
        Index("ix_outbox_event_contest", "tenant_id", "contest_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str] = mapped_column(String(36), ForeignKey("contest.id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
