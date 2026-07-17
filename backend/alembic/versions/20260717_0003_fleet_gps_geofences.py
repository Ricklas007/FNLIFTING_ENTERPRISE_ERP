from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

from app.database.base import Base


revision = "20260717_0003"
down_revision = "20260712_0002"
branch_labels = None
depends_on = None

TABLES = {
    "gps_tracker_devices",
    "geofences",
    "geofence_events",
    "fleet_alert_rules",
    "fleet_alerts",
}


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name in TABLES and table.name not in existing_tables:
            table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in TABLES:
            table.drop(bind=bind, checkfirst=True)
