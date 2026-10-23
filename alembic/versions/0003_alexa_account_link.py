"""Persist dashboard repository selection and Alexa account links.

Revision ID: 0003_alexa_account_link
Revises: 0002_preferred_org_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_alexa_account_link"
down_revision: Union[str, None] = "0002_preferred_org_id"
branch_labels: Union[str, Sequence[str] | None] = None
depends_on: Union[str, Sequence[str] | None] = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "selected_repository" not in columns:
        op.add_column("users", sa.Column("selected_repository", sa.String(255), nullable=True))

    op.create_table(
        "alexa_pairing_codes",
        sa.Column("code_digest", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("selected_repository", sa.String(255), nullable=False),
        sa.Column("encrypted_github_token", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_alexa_pairing_codes_user_id", "alexa_pairing_codes", ["user_id"])
    op.create_index("ix_alexa_pairing_codes_expires_at", "alexa_pairing_codes", ["expires_at"])

    op.create_table(
        "alexa_account_links",
        sa.Column("alexa_user_id", sa.String(255), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("encrypted_github_token", sa.Text(), nullable=False),
        sa.Column("linked_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_alexa_account_links_user_id", "alexa_account_links", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_alexa_account_links_user_id", table_name="alexa_account_links")
    op.drop_table("alexa_account_links")
    op.drop_index("ix_alexa_pairing_codes_expires_at", table_name="alexa_pairing_codes")
    op.drop_index("ix_alexa_pairing_codes_user_id", table_name="alexa_pairing_codes")
    op.drop_table("alexa_pairing_codes")
    op.drop_column("users", "selected_repository")
