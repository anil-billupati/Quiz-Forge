"""Wildcard runtime: wildcard_activation table + nullable selected_option_id (Unit 11).

Revision ID: 0014_wildcard_activation
Revises: 0013_score
Create Date: 2026-06-26

Adds the wildcard_activation table (durable, at-most-once activation log; FR-26
unique per type/participant/contest) and relaxes answer_submission.selected_option_id
to nullable so a SKIPPED answer can be recorded with no selected option (FR-25).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_wildcard_activation"
down_revision: str | None = "0013_score"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wildcard_activation",
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
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id",
            "contest_id",
            "participant_id",
            "type",
            name="uq_wildcard_activation_once_per_contest",
        ),
    )
    op.create_index(
        "ix_wildcard_activation_contest",
        "wildcard_activation",
        ["tenant_id", "contest_id", "participant_id"],
    )

    # SKIP records an answer with no selected option (FR-25).
    with op.batch_alter_table("answer_submission") as batch:
        batch.alter_column("selected_option_id", existing_type=sa.String(length=36), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("answer_submission") as batch:
        batch.alter_column("selected_option_id", existing_type=sa.String(length=36), nullable=False)

    op.drop_index("ix_wildcard_activation_contest", table_name="wildcard_activation")
    op.drop_table("wildcard_activation")
