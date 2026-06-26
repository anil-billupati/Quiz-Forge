"""Wildcard configuration (F9).

Revision ID: 0006_wildcard_config
Revises: 0005_configuration_blocks
Create Date: 2026-06-23

Creates the wildcard_config table per ConfigurationBlock (domain-model §2,
FR-22/26). Enforces at most one config per wildcard type per block.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_wildcard_config"
down_revision: str | None = "0005_configuration_blocks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wildcard_config",
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
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("eligibility", sa.String(length=16), nullable=False, server_default="ALL"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "config_block_id", "type", name="uq_wildcard_block_type"
        ),
    )
    op.create_index("ix_wildcard_config_block", "wildcard_config", ["tenant_id", "config_block_id"])


def downgrade() -> None:
    op.drop_index("ix_wildcard_config_block", table_name="wildcard_config")
    op.drop_table("wildcard_config")
