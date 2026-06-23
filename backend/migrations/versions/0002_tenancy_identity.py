"""Tenancy & Identity: organization, tenant_settings, user, refresh_token, usage.

Revision ID: 0002_tenancy_identity
Revises: 0001_foundation
Create Date: 2026-06-22

Creates the Unit 2 tables with their uniqueness and isolation constraints
(ADR-001, domain-model §2). Includes the partial unique index that enforces
platform-wide uniqueness of SUPER_ADMIN emails.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_tenancy_identity"
down_revision: Union[str, None] = "0001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("portal_url", sa.String(length=512), nullable=False),
        sa.Column("custom_domain", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("has_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_organization_slug"),
        sa.UniqueConstraint("portal_url", name="uq_organization_portal_url"),
        sa.UniqueConstraint("custom_domain", name="uq_organization_custom_domain"),
    )

    op.create_table(
        "tenant_settings",
        sa.Column(
            "organization_id",
            sa.String(length=36),
            sa.ForeignKey("organization.id"),
            primary_key=True,
        ),
        sa.Column("max_concurrent_live_contests", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "max_participants_per_contest", sa.Integer(), nullable=False, server_default="10000"
        ),
        sa.Column("max_questions_per_contest", sa.Integer(), nullable=False, server_default="200"),
        sa.Column(
            "default_negative_marking", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_account",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=True
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )
    op.create_index("ix_user_tenant_id", "user_account", ["tenant_id"])
    op.create_index("ix_user_email", "user_account", ["email"])
    # Platform-wide uniqueness of SUPER_ADMIN emails (Postgres partial index).
    op.execute(
        """
        CREATE UNIQUE INDEX uq_super_admin_email
        ON user_account (email) WHERE role = 'SUPER_ADMIN'
        """
    )

    op.create_table(
        "refresh_token",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_family", sa.String(length=36), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.String(length=36), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_refresh_token_hash"),
    )
    op.create_index("ix_refresh_token_user_id", "refresh_token", ["user_id"])
    op.create_index("ix_refresh_token_family", "refresh_token", ["token_family"])

    op.create_table(
        "tenant_usage_record",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contests_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("live_contest_peak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("participant_minutes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("questions_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answer_submissions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("wildcard_activations", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("storage_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.UniqueConstraint("tenant_id", "period_start", name="uq_usage_tenant_period"),
    )
    op.create_index("ix_usage_tenant_id", "tenant_usage_record", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("tenant_usage_record")
    op.drop_table("refresh_token")
    op.execute("DROP INDEX IF EXISTS uq_super_admin_email")
    op.drop_index("ix_user_email", table_name="user_account")
    op.drop_index("ix_user_tenant_id", table_name="user_account")
    op.drop_table("user_account")
    op.drop_table("tenant_settings")
    op.drop_table("organization")
