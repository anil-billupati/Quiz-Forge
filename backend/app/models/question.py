"""Question and Option models (domain-model §2, FR authoring, BR-21).

A Question belongs to a Contest (Normal structure) and optionally a Group
(Grouped structure). Each Question has ≥2 Options with exactly one correct
(BR-21). Questions and options are authored while the contest is in DRAFT.
Runtime reveal timing lives on QuestionWindow, not here.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantScoped, new_uuid


class Question(Base, TenantScoped):
    __tablename__ = "question"
    __table_args__ = (
        Index("ix_question_contest", "tenant_id", "contest_id"),
        Index("ix_question_group", "tenant_id", "group_id"),
        # Sequence is unique within a contest (Normal) or within a group (Grouped).
        Index(
            "uq_question_contest_seq",
            "tenant_id",
            "contest_id",
            "sequence",
            unique=True,
            postgresql_where=text("group_id IS NULL"),
            sqlite_where=text("group_id IS NULL"),
        ),
        Index(
            "uq_question_group_seq",
            "tenant_id",
            "group_id",
            "sequence",
            unique=True,
            postgresql_where=text("group_id IS NOT NULL"),
            sqlite_where=text("group_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    contest_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contest.id"), nullable=False
    )
    group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contest_group.id"), nullable=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    options: Mapped[list[Option]] = relationship(
        "Option", cascade="all, delete-orphan", lazy="selectin", order_by="Option.ordinal"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Option(Base, TenantScoped):
    __tablename__ = "option"
    __table_args__ = (
        UniqueConstraint("tenant_id", "question_id", "ordinal", name="uq_option_question_ordinal"),
        # Exactly one correct option per question (BR-21).
        Index(
            "uq_option_one_correct",
            "tenant_id",
            "question_id",
            unique=True,
            postgresql_where=text("is_correct"),
            sqlite_where=text("is_correct = 1"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("question.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
