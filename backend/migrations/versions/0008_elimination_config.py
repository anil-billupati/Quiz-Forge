"""Elimination configuration: rules + checkpoints (F8/BR-4).

Revision ID: 0008_elimination_config
Revises: 0007_global_unique_user_email
Create Date: 2026-06-25

Adds the elimination_rule and checkpoint tables — children of a
ConfigurationBlock used only in ELIMINATION mode (domain-model §2, FR-33/34/35,
BR-4). Both are tenant-scoped and reference the parent block.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_elimination_config"
down_revision: str | None = "0007_global_unique_user_email"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "elimination_rule",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column(
            "config_block_id",
            sa.String(length=36),
            sa.ForeignKey("configuration_block.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("n_value", sa.Integer(), nullable=True),
        sa.Column("percent_value", sa.Numeric(5, 2), nullable=True),
        sa.Column("min_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "type IN ('FIRST_WRONG', 'N_WRONG', 'BOTTOM_X_PERCENT', 'MIN_SCORE')",
            name="ck_elimination_rule_type",
        ),
    )
    op.create_index(
        "ix_elimination_rule_block", "elimination_rule", ["tenant_id", "config_block_id"]
    )

    op.create_table(
        "checkpoint",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column(
            "config_block_id",
            sa.String(length=36),
            sa.ForeignKey("configuration_block.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("question_sequence", sa.Integer(), nullable=True),
        sa.Column("milestone_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "type IN ('AFTER_QUESTION', 'AFTER_GROUP', 'CUSTOM_MILESTONE')",
            name="ck_checkpoint_type",
        ),
    )
    op.create_index("ix_checkpoint_block", "checkpoint", ["tenant_id", "config_block_id"])


def downgrade() -> None:
    op.drop_index("ix_checkpoint_block", table_name="checkpoint")
    op.drop_table("checkpoint")
    op.drop_index("ix_elimination_rule_block", table_name="elimination_rule")
    op.drop_table("elimination_rule")
