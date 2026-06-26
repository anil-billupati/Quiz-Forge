"""Configuration blocks (F8).

Revision ID: 0005_configuration_blocks
Revises: 0004_groups
Create Date: 2026-06-23

Creates the configuration_block table for contest/group run configuration
(domain-model §2, FR-10, BR-20). Enforces exactly-one-of (contest_id, group_id)
and partial unique indexes so a Normal contest has one block and each Group has
one block.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_configuration_blocks"
down_revision: str | None = "0004_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "configuration_block",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), nullable=True),
        sa.Column(
            "group_id", sa.String(length=36), sa.ForeignKey("contest_group.id"), nullable=True
        ),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("question_duration_s", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("question_interval_s", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("explanation_duration_s", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("leaderboard_duration_s", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("reveal_mode", sa.String(length=24), nullable=False, server_default="AUTOMATIC"),
        sa.Column(
            "ranking_criterion", sa.String(length=16), nullable=False, server_default="SCORE_ONLY"
        ),
        sa.Column("tie_display", sa.String(length=16), nullable=False, server_default="SHARED_RANK"),
        sa.Column(
            "leaderboard_visibility", sa.String(length=16), nullable=False, server_default="POST_QUESTION"
        ),
        sa.Column(
            "update_frequency", sa.String(length=16), nullable=False, server_default="PER_QUESTION"
        ),
        sa.Column("elimination_combine_operator", sa.String(length=8), nullable=True),
        sa.Column("survivor_score_reset", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scoring_model", sa.String(length=16), nullable=False),
        sa.Column("scoring_config", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "(contest_id IS NOT NULL AND group_id IS NULL) OR (contest_id IS NULL AND group_id IS NOT NULL)",
            name="ck_configuration_block_one_scope",
        ),
        sa.CheckConstraint("question_duration_s BETWEEN 5 AND 300", name="ck_question_duration"),
        sa.CheckConstraint("question_interval_s BETWEEN 0 AND 60", name="ck_question_interval"),
        sa.CheckConstraint(
            "explanation_duration_s BETWEEN 0 AND 60", name="ck_explanation_duration"
        ),
        sa.CheckConstraint(
            "leaderboard_duration_s BETWEEN 0 AND 60", name="ck_leaderboard_duration"
        ),
    )
    op.create_index("ix_config_block_tenant_id", "configuration_block", ["tenant_id"])
    op.create_index("ix_config_block_contest", "configuration_block", ["tenant_id", "contest_id"])
    op.create_index("ix_config_block_group", "configuration_block", ["tenant_id", "group_id"])
    op.create_index(
        "uq_config_block_contest",
        "configuration_block",
        ["tenant_id", "contest_id"],
        unique=True,
        postgresql_where=sa.text("group_id IS NULL"),
    )
    op.create_index(
        "uq_config_block_group",
        "configuration_block",
        ["tenant_id", "group_id"],
        unique=True,
        postgresql_where=sa.text("contest_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_config_block_group", table_name="configuration_block")
    op.drop_index("uq_config_block_contest", table_name="configuration_block")
    op.drop_index("ix_config_block_group", table_name="configuration_block")
    op.drop_index("ix_config_block_contest", table_name="configuration_block")
    op.drop_index("ix_config_block_tenant_id", table_name="configuration_block")
    op.drop_table("configuration_block")
