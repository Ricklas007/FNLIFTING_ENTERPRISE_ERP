from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    AIProviderSetting, AutomationRule, Certificate, ComplianceRequirement, DeviceRegistration,
    Document, FleetCommand, OCRJob, SaaSLicense, Trip, User, UserMFAFactor,
)
from app.services.enterprise_utils import sync_provider_hint, to_json


def ensure_enterprise_seed(db: Session, user: User) -> None:
    company_id = user.company_id
    today = date.today()
    previous_skip_sync = db.info.get("skip_sync_queue", False)
    db.info["skip_sync_queue"] = True
    try:
        providers = [
            ("ocr", "local-ocr", "local"),
            ("rules", "local-rules", "local"),
            ("notifications", "local-notifications", "local"),
            ("sync", sync_provider_hint(), "cloud" if settings.sync_remote_url else "local"),
        ]
        for provider_type, provider_name, mode in providers:
            exists = db.scalar(select(AIProviderSetting).where(
                AIProviderSetting.company_id == company_id,
                AIProviderSetting.provider_type == provider_type,
                AIProviderSetting.provider_name == provider_name,
                AIProviderSetting.deleted_at.is_(None),
            ))
            if not exists:
                db.add(AIProviderSetting(
                    company_id=company_id,
                    provider_type=provider_type,
                    provider_name=provider_name,
                    mode=mode,
                    endpoint_url=settings.sync_remote_url if provider_type == "sync" and settings.sync_remote_url else None,
                    status="active",
                    created_by=user.id,
                ))

        rules = [
            ("CERT_EXP_45", "Alertar certificados a 45 dias do vencimento", "certificates", {"days_to_expire_lte": 45}, {"notify": ["operations", "client_portal"]}, "warning"),
            ("GPS_IDLE_60", "Sinalizar camião parado há mais de 60 minutos", "fleet", {"vehicle_state": "idle", "minutes_gte": 60}, {"open_command": "contact_driver"}, "warning"),
            ("DOC_APPROVAL", "Enviar documentos críticos para aprovação", "documents", {"approval_status": "pending"}, {"queue": "approval_center"}, "info"),
        ]
        for code, name, module, condition, action, severity in rules:
            exists = db.scalar(select(AutomationRule).where(AutomationRule.company_id == company_id, AutomationRule.code == code, AutomationRule.deleted_at.is_(None)))
            if not exists:
                db.add(AutomationRule(
                    company_id=company_id,
                    code=code,
                    name=name,
                    module=module,
                    trigger_event="scheduled.daily",
                    condition_json=to_json(condition),
                    action_json=to_json(action),
                    severity=severity,
                    status="active",
                    created_by=user.id,
                ))

        for code, title, category, authority, risk in [
            ("ISO-9001-DOC", "Revisão documental do sistema de qualidade", "Qualidade", "ISO 9001", "medium"),
            ("LIFT-CERT-EXP", "Controlo de certificados de elevação próximos do vencimento", "Operações", "FNLIFTING", "high"),
            ("DATA-BACKUP", "Evidência de backup cifrado e testado", "Segurança", "FNLIFTING", "high"),
        ]:
            exists = db.scalar(select(ComplianceRequirement).where(ComplianceRequirement.company_id == company_id, ComplianceRequirement.code == code, ComplianceRequirement.deleted_at.is_(None)))
            if not exists:
                db.add(ComplianceRequirement(
                    company_id=company_id,
                    code=code,
                    title=title,
                    category=category,
                    authority=authority,
                    due_date=today + timedelta(days=90),
                    risk_level=risk,
                    status="open",
                    created_by=user.id,
                ))

        license_record = db.scalar(select(SaaSLicense).where(SaaSLicense.company_id == company_id, SaaSLicense.deleted_at.is_(None)))
        if not license_record:
            db.add(SaaSLicense(
                company_id=company_id,
                plan_code="enterprise-local",
                seats=50,
                modules_json=to_json(["core", "certificates", "fleet", "hr", "ai", "bi", "portal", "compliance"]),
                starts_at=today,
                expires_at=today + timedelta(days=365),
                status="active",
                usage_json=to_json({"mode": "local-first", "remote_configured": bool(settings.sync_remote_url)}),
                created_by=user.id,
            ))
        db.flush()
    finally:
        db.info["skip_sync_queue"] = previous_skip_sync


def enterprise_overview(db: Session, user: User) -> dict[str, Any]:
    ensure_enterprise_seed(db, user)
    company_id = user.company_id
    today = date.today()
    mfa_enabled = bool(db.scalar(select(UserMFAFactor.id).where(UserMFAFactor.user_id == user.id, UserMFAFactor.status == "active", UserMFAFactor.confirmed_at.is_not(None))))
    return {
        "version": f"{settings.app_version}-local",
        "provider_mode": sync_provider_hint(),
        "remote_configured": bool(settings.sync_remote_url),
        "phases": [
            {"phase": 8, "title": "Cloud, Sync 2.0, MFA e notificações", "status": "active"},
            {"phase": 9, "title": "Frota, GPS e logística", "status": "active"},
            {"phase": 10, "title": "IA, OCR e automações", "status": "active"},
            {"phase": 11, "title": "RH enterprise e payroll", "status": "active"},
            {"phase": 12, "title": "BI, compliance e SaaS", "status": "active"},
        ],
        "metrics": {
            "registered_devices": db.scalar(select(func.count(DeviceRegistration.id)).where(DeviceRegistration.company_id == company_id, DeviceRegistration.deleted_at.is_(None))) or 0,
            "unread_notifications": 0,
            "sync_events": 0,
            "fleet_commands_open": db.scalar(select(func.count(FleetCommand.id)).where(FleetCommand.company_id == company_id, FleetCommand.status == "open", FleetCommand.deleted_at.is_(None))) or 0,
            "ocr_jobs": db.scalar(select(func.count(OCRJob.id)).where(OCRJob.company_id == company_id, OCRJob.deleted_at.is_(None))) or 0,
            "payroll_runs": 0,
            "compliance_open": db.scalar(select(func.count(ComplianceRequirement.id)).where(ComplianceRequirement.company_id == company_id, ComplianceRequirement.status == "open", ComplianceRequirement.deleted_at.is_(None))) or 0,
            "certificates_expiring": db.scalar(select(func.count(Certificate.id)).where(Certificate.company_id == company_id, Certificate.status == "issued", Certificate.expires_at.between(today, today + timedelta(days=45)), Certificate.deleted_at.is_(None))) or 0,
            "documents_pending": db.scalar(select(func.count(Document.id)).where(Document.company_id == company_id, Document.approval_status == "pending", Document.deleted_at.is_(None))) or 0,
            "active_trips": db.scalar(select(func.count(Trip.id)).where(Trip.company_id == company_id, Trip.status.in_(["planned", "in_progress", "delayed"]), Trip.deleted_at.is_(None))) or 0,
        },
        "security": {"mfa_enabled": mfa_enabled},
    }
