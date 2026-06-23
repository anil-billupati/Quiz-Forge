"""Foundation: extensions + tenant-scoped probe table.

Revision ID: 0001_foundation
Revises:
Create Date: 2026-06-22

Establishes the migration pipeline (Unit 1). Enables the pgcrypto extension
(UUID generation for later units) and creates the `_foundation_probe`
tenant-scoped table used to validate tenant isolation. Row-Level Security is
enabled on the probe table as the defence-in-depth pattern all tenant-scoped
tables follow (ADR-001, technical-spec §7.1).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "_foundation_probe",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
    )
    op.create_index(
        "ix__foundation_probe_tenant_id", "_foundation_probe", ["tenant_id"]
    )

    # RLS scaffolding (defence in depth). The application sets
    # `app.tenant_id` per transaction; the policy restricts visible rows.
    op.execute("ALTER TABLE _foundation_probe ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON _foundation_probe
        USING (tenant_id = current_setting('app.tenant_id', true))
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON _foundation_probe")
    op.drop_index("ix__foundation_probe_tenant_id", table_name="_foundation_probe")
    op.drop_table("_foundation_probe")
