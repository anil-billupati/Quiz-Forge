"""Contest groups: contest_group (F7).

Revision ID: 0004_groups
Revises: 0003_contest_authoring
Create Date: 2026-06-23

Creates the group table for GROUPED contests (domain-model §2, FR-8). Sequence
is unique within a contest. Tenant-scoped.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_groups"
down_revision: str | None = "0003_contest_authoring"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contest_group",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "contest_id", "sequence", name="uq_group_contest_sequence"
        ),
    )
    op.create_index("ix_group_tenant_id", "contest_group", ["tenant_id"])
    op.create_index("ix_group_contest", "contest_group", ["tenant_id", "contest_id"])


def downgrade() -> None:
    op.drop_index("ix_group_contest", table_name="contest_group")
    op.drop_index("ix_group_tenant_id", table_name="contest_group")
    op.drop_table("contest_group")
