"""Baseline schema for GreenCode Auditor.

This is a *baseline* rather than a generated DDL dump: it delegates to the same
``Base.metadata`` the application uses, so the schema can never drift between
the models and the migration. That also means adopting an existing database is
safe - if the tables are already there, this becomes a no-op rather than an
error, which matters because ``init_db()`` may have created them already.

    revision = "0001_baseline"
"""
from typing import Sequence, Union

from alembic import op

from app.database import Base

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # checkfirst=True (the default) makes this idempotent: CREATE TABLE for
    # anything missing, nothing for what already exists.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Deliberately empty. Dropping the baseline would delete the users table
    # and every audit record with it. To reset a development database, drop it
    # and re-create rather than running `alembic downgrade base`.
    pass
