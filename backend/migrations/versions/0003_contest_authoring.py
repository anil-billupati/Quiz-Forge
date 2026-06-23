"""Contest authoring & lifecycle: contest, contest_lifecycle_event (F6).

Revision ID: 0003_contest_authoring
Revises: 0002_tenancy_identity
Create Date: 2026-06-23

Creates the Unit 3 contest table and its append-only lifecycle audit
(domain-model §2, FR-6/7/9). Both are tenant-scoped.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_contest_authoring"
down_revision: str | None = "0002_tenancy_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contest",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("structure", sa.String(length=16), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=24), nullable=False, server_default="DRAFT"),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("group_score_rollup", sa.String(length=16), nullable=True),
        sa.Column("rollup_best_n", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_contest_tenant_id", "contest", ["tenant_id"])
    op.create_index("ix_contest_tenant_status", "contest", ["tenant_id", "lifecycle_status"])

    op.create_table(
        "contest_lifecycle_event",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), nullable=False),
        sa.Column("previous_status", sa.String(length=24), nullable=False),
        sa.Column("new_status", sa.String(length=24), nullable=False),
        sa.Column("triggered_by", sa.String(length=36), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lifecycle_event_tenant_id", "contest_lifecycle_event", ["tenant_id"])
    op.create_index(
        "ix_lifecycle_event_contest",
        "contest_lifecycle_event",
        ["tenant_id", "contest_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("contest_lifecycle_event")
    op.drop_index("ix_contest_tenant_status", table_name="contest")
    op.drop_index("ix_contest_tenant_id", table_name="contest")
    op.drop_table("contest")
