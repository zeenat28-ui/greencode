"""Add preferred_org_id column to users table for tenant switching.

Revision ID: 0002_preferred_org_id
Revises: 0001_baseline
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_preferred_org_id"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str] | None] = None
depends_on: Union[str, Sequence[str] | None] = None


def upgrade() -> None:
    """Add preferred_org_id column to users table.

    The column is nullable for backwards compatibility: existing users keep
    their org_id as the default preferred org until they switch via the
    /api/tenants/switch endpoint.
    """
    op.add_column(
        "users",
        sa.Column(
            "preferred_org_id",
            sa.Integer,
            sa.ForeignKey("organizations.id"),
            nullable=True,
            index=True,
        ),
    )
    # Backfill: set preferred_org_id = org_id for all existing users
    op.execute(
        "UPDATE users SET preferred_org_id = org_id "
        "WHERE preferred_org_id IS NULL AND org_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("users", "preferred_org_id")
