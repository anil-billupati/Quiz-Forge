"""Execution engine: contest execution state + question windows (Unit 8).

Revision ID: 0011_execution_state
Revises: 0010_registration
Create Date: 2026-06-25

Adds contest_execution_state (singleton durable engine state per contest, for
recovery) and question_window (authoritative server-side timing per question run;
submission_close_at is the answer-acceptance authority, FR-20).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_execution_state"
down_revision: str | None = "0010_registration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contest_execution_state",
        sa.Column("contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column(
            "current_group_id", sa.String(length=36), sa.ForeignKey("contest_group.id"), nullable=True
        ),
        sa.Column(
            "current_question_id", sa.String(length=36), sa.ForeignKey("question.id"), nullable=True
        ),
        sa.Column("phase", sa.String(length=16), nullable=False, server_default="DISPLAY"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "question_window",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), nullable=False),
        sa.Column(
            "group_id", sa.String(length=36), sa.ForeignKey("contest_group.id"), nullable=True
        ),
        sa.Column("question_id", sa.String(length=36), sa.ForeignKey("question.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("revealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submission_close_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "contest_id", "question_id", name="uq_question_window_contest_question"
        ),
    )
    op.create_index(
        "ix_question_window_seq", "question_window", ["tenant_id", "contest_id", "sequence"]
    )


def downgrade() -> None:
    op.drop_index("ix_question_window_seq", table_name="question_window")
    op.drop_table("question_window")
    op.drop_table("contest_execution_state")
