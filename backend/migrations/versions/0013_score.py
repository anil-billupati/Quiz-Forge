"""Scoring engine: score table + answer_submission scoring inputs (Unit 10).

Revision ID: 0013_score
Revises: 0012_answer_submission
Create Date: 2026-06-26

Adds the score table (at-most-once per answer submission, BR-8) and the scoring
input columns on answer_submission (outcome, response_time_ms, scored).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_score"
down_revision: str | None = "0012_answer_submission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("answer_submission", sa.Column("outcome", sa.String(length=16), nullable=True))
    op.add_column(
        "answer_submission", sa.Column("response_time_ms", sa.Integer(), nullable=True)
    )
    op.add_column(
        "answer_submission",
        sa.Column("scored", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "score",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column(
            "contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), nullable=False
        ),
        sa.Column(
            "group_id", sa.String(length=36), sa.ForeignKey("contest_group.id"), nullable=True
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
            "answer_submission_id",
            sa.String(length=36),
            sa.ForeignKey("answer_submission.id"),
            nullable=False,
        ),
        sa.Column("scoring_model", sa.String(length=16), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "answer_submission_id", name="uq_score_answer_submission"
        ),
    )
    op.create_index(
        "ix_score_contest_participant", "score", ["tenant_id", "contest_id", "participant_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_score_contest_participant", table_name="score")
    op.drop_table("score")
    op.drop_column("answer_submission", "scored")
    op.drop_column("answer_submission", "response_time_ms")
    op.drop_column("answer_submission", "outcome")
