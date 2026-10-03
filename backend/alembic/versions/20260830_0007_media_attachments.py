from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

from app.database.base import Base
from app.models import MediaAttachment  # noqa: F401


revision = "20260830_0007"
down_revision = "20260802_0006"
branch_labels = None
depends_on = None

TABLES = {"media_attachments"}


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name in TABLES and table.name not in existing_tables:
            table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in TABLES and table.name in existing_tables:
            table.drop(bind=bind, checkfirst=True)
