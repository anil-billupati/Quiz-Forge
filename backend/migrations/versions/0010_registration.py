"""Registration (Unit 6).

Revision ID: 0010_registration
Revises: 0009_questions_options
Create Date: 2026-06-25

Adds the registration table linking a participant (User) to a Contest. Unique per
(tenant, contest, participant); indexed by (tenant, contest, status) for roster
queries.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_registration"
down_revision: str | None = "0009_questions_options"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "registration",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False
        ),
        sa.Column("contest_id", sa.String(length=36), sa.ForeignKey("contest.id"), nullable=False),
        sa.Column(
            "participant_id",
            sa.String(length=36),
            sa.ForeignKey("user_account.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="REGISTERED"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("spectator_access", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("final_rank", sa.Integer(), nullable=True),
        sa.Column("final_score", sa.Integer(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "contest_id", "participant_id", name="uq_registration_contest_participant"
        ),
    )
    op.create_index(
        "ix_registration_contest_status",
        "registration",
        ["tenant_id", "contest_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_registration_contest_status", table_name="registration")
    op.drop_table("registration")
