"""Answer submission and transactional outbox (Unit 9).

Revision ID: 0012_answer_submission
Revises: 0011_execution_state
Create Date: 2026-06-25

Adds answer_submission (durable answer intake with idempotency hash) and
outbox_event (transactional outbox for scoring commands, ADR-002).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_answer_submission"
down_revision: str | None = "0011_execution_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answer_submission",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column(
            "contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), nullable=False
        ),
        sa.Column(
            "question_id", sa.String(length=36), sa.ForeignKey("question.id"), nullable=False
        ),
        sa.Column(
            "participant_id",
            sa.String(length=36),
            sa.ForeignKey("user_account.id"),
            nullable=False,
        ),
        sa.Column(
            "registration_id",
            sa.String(length=36),
            sa.ForeignKey("registration.id"),
            nullable=False,
        ),
        sa.Column(
            "selected_option_id", sa.String(length=36), sa.ForeignKey("option.id"), nullable=False
        ),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("rejection_reason", sa.String(length=32), nullable=True),
        sa.Column("server_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_hash", name="uq_answer_submission_idempotency"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "contest_id",
            "question_id",
            "participant_id",
            "attempt_no",
            name="uq_answer_submission_natural_key",
        ),
    )
    op.create_index(
        "ix_answer_submission_contest_status",
        "answer_submission",
        ["tenant_id", "contest_id", "status"],
    )

    op.create_table(
        "outbox_event",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column(
            "contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), nullable=False
        ),
        sa.Column("topic", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_outbox_event_status_created", "outbox_event", ["status", "created_at"]
    )
    op.create_index(
        "ix_outbox_event_contest", "outbox_event", ["tenant_id", "contest_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_event_contest", table_name="outbox_event")
    op.drop_index("ix_outbox_event_status_created", table_name="outbox_event")
    op.drop_table("outbox_event")
    op.drop_index("ix_answer_submission_contest_status", table_name="answer_submission")
    op.drop_table("answer_submission")
