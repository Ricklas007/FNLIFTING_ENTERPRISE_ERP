from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

from app.database.base import Base


revision = "20260712_0002"
down_revision = "20260707_0001"
branch_labels = None
depends_on = None

TABLES = {
    "ai_provider_settings",
    "attendance_records",
    "automation_rules",
    "automation_runs",
    "compliance_requirements",
    "customer_messages",
    "device_registrations",
    "enterprise_sync_events",
    "fleet_commands",
    "gps_integration_events",
    "leave_requests",
    "mfa_challenges",
    "mfa_recovery_codes",
    "notification_deliveries",
    "ocr_jobs",
    "payroll_items",
    "payroll_runs",
    "saas_licenses",
    "security_events",
    "user_mfa_factors",
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
