from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

from app.database.base import Base


revision = "20260707_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the Phase 1-7 baseline schema when bootstrapping a new database."""
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)

