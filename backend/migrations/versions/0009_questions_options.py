"""Questions & options authoring (Unit 5, BR-21).

Revision ID: 0009_questions_options
Revises: 0008_elimination_config
Create Date: 2026-06-25

Adds the question and option tables. Questions are scoped to a contest (and
optionally a group); sequence is unique within a contest (Normal) or within a
group (Grouped) via partial unique indexes. Each question has exactly one correct
option, enforced by a partial unique index (BR-21).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_questions_options"
down_revision: str | None = "0008_elimination_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "question",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), nullable=False),
        sa.Column(
            "group_id", sa.String(length=36), sa.ForeignKey("contest_group.id"), nullable=True
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_question_contest", "question", ["tenant_id", "contest_id"])
    op.create_index("ix_question_group", "question", ["tenant_id", "group_id"])
    op.create_index(
        "uq_question_contest_seq",
        "question",
        ["tenant_id", "contest_id", "sequence"],
        unique=True,
        postgresql_where=sa.text("group_id IS NULL"),
    )
    op.create_index(
        "uq_question_group_seq",
        "question",
        ["tenant_id", "group_id", "sequence"],
        unique=True,
        postgresql_where=sa.text("group_id IS NOT NULL"),
    )

    op.create_table(
        "option",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("question_id", sa.String(length=36), sa.ForeignKey("question.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "question_id", "ordinal", name="uq_option_question_ordinal"),
    )
    op.create_index(
        "uq_option_one_correct",
        "option",
        ["tenant_id", "question_id"],
        unique=True,
        postgresql_where=sa.text("is_correct"),
    )


def downgrade() -> None:
    op.drop_index("uq_option_one_correct", table_name="option")
    op.drop_table("option")
    op.drop_index("uq_question_group_seq", table_name="question")
    op.drop_index("uq_question_contest_seq", table_name="question")
    op.drop_index("ix_question_group", table_name="question")
    op.drop_index("ix_question_contest", table_name="question")
    op.drop_table("question")
