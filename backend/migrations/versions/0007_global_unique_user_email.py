"""Global unique user email.

Revision ID: 0007_global_unique_user_email
Revises: 0006_wildcard_config
Create Date: 2026-06-24

Login no longer takes a tenant hint: the email alone identifies the account and
its tenant. This requires email to be globally unique across all tenants and
platform users, replacing the previous per-tenant uniqueness
(uq_user_tenant_email) and the now-redundant SUPER_ADMIN partial index
(uq_super_admin_email).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0007_global_unique_user_email"
down_revision: str | None = "0006_wildcard_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_user_tenant_email", "user_account", type_="unique")
    op.drop_index("uq_super_admin_email", table_name="user_account")
    op.create_unique_constraint("uq_user_email", "user_account", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_user_email", "user_account", type_="unique")
    op.create_unique_constraint(
        "uq_user_tenant_email", "user_account", ["tenant_id", "email"]
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_super_admin_email
        ON user_account (email) WHERE role = 'SUPER_ADMIN'
        """
    )
