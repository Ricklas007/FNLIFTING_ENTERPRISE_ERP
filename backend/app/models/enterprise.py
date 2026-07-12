"""Compatibility exports for enterprise phase models.

Concrete model definitions live in domain-specific modules so Alembic and
runtime imports remain maintainable while older imports from app.models keep
working.
"""

from app.models.ai import AIProviderSetting, AutomationRule, AutomationRun, OCRJob
from app.models.compliance import ComplianceRequirement
from app.models.fleet_enterprise import FleetCommand
from app.models.gps import GPSIntegrationEvent
from app.models.hr_enterprise import AttendanceRecord, LeaveRequest
from app.models.licensing import SaaSLicense
from app.models.notifications import NotificationDelivery
from app.models.payroll import PayrollItem, PayrollRun
from app.models.security import DeviceRegistration, MFAChallenge, MFARecoveryCode, SecurityEvent, UserMFAFactor
from app.models.sync import EnterpriseSyncEvent
from app.models.tenancy import CustomerMessage

__all__ = [
    "AIProviderSetting",
    "AttendanceRecord",
    "AutomationRule",
    "AutomationRun",
    "ComplianceRequirement",
    "CustomerMessage",
    "DeviceRegistration",
    "EnterpriseSyncEvent",
    "FleetCommand",
    "GPSIntegrationEvent",
    "LeaveRequest",
    "MFAChallenge",
    "MFARecoveryCode",
    "NotificationDelivery",
    "OCRJob",
    "PayrollItem",
    "PayrollRun",
    "SaaSLicense",
    "SecurityEvent",
    "UserMFAFactor",
]
