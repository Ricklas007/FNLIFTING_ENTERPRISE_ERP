import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.database.session import get_db
from app.models import DeviceRegistration, SecurityEvent, User
from app.schemas.enterprise import DeviceRegisterRequest, MFAConfirmRequest
from app.services import mfa_service, session_service
from app.services.enterprise_utils import from_json, now_utc, to_json

router = APIRouter()


def record_security_event(db: Session, user: User, request: Request, event_type: str, severity: str = "info", detail: dict[str, Any] | None = None) -> None:
    db.add(SecurityEvent(
        company_id=user.company_id,
        user_id=user.id,
        event_type=event_type,
        severity=severity,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
        detail_json=to_json(detail or {}),
        created_by=user.id,
    ))


def device_out(device: DeviceRegistration) -> dict[str, Any]:
    return {
        "id": device.id,
        "device_uid": device.device_uid,
        "name": device.name,
        "platform": device.platform,
        "app_version": device.app_version,
        "capabilities": from_json(device.capabilities_json, []),
        "trust_level": device.trust_level,
        "status": device.status,
        "last_seen_at": device.last_seen_at,
        "created_at": device.created_at,
    }


@router.post("/devices/register", status_code=201)
def register_device(payload: DeviceRegisterRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.scalar(select(DeviceRegistration).where(DeviceRegistration.company_id == user.company_id, DeviceRegistration.device_uid == payload.device_uid, DeviceRegistration.deleted_at.is_(None)))
    if not device:
        device = DeviceRegistration(company_id=user.company_id, device_uid=payload.device_uid, created_by=user.id)
        db.add(device)
    device.user_id = user.id
    device.name = payload.name
    device.platform = payload.platform
    device.app_version = payload.app_version
    device.capabilities_json = json.dumps(payload.capabilities, ensure_ascii=False)
    device.public_key = payload.public_key
    device.last_seen_at = now_utc()
    device.status = "active"
    device.updated_by = user.id
    record_security_event(db, user, request, "device.registered", "info", {"device_uid": payload.device_uid, "platform": payload.platform})
    db.commit()
    db.refresh(device)
    return device_out(device)


@router.get("/devices")
def list_devices(user: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)):
    rows = db.scalars(select(DeviceRegistration).where(DeviceRegistration.company_id == user.company_id, DeviceRegistration.deleted_at.is_(None)).order_by(DeviceRegistration.last_seen_at.desc()))
    return [device_out(row) for row in rows]


@router.get("/sessions")
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return session_service.list_user_sessions(db, user)


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: str, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not session_service.revoke_user_session(db, user, session_id):
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    record_security_event(db, user, request, "session.revoked", "info", {"session_id": session_id})
    db.commit()
    return {"message": "Sessão revogada"}


@router.post("/security/mfa/setup")
def setup_mfa(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = mfa_service.start_setup(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_security_event(db, user, request, "mfa.setup.started")
    db.commit()
    return result


@router.post("/security/mfa/confirm")
def confirm_mfa(payload: MFAConfirmRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    codes = mfa_service.confirm_setup(db, user, payload.code)
    if codes is None:
        raise HTTPException(status_code=400, detail="Código MFA inválido")
    record_security_event(db, user, request, "mfa.enabled", "warning")
    db.commit()
    return {"message": "MFA ativado com sucesso", "recovery_codes": codes}


@router.post("/security/mfa/disable")
def disable_mfa(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mfa_service.disable_mfa(db, user)
    record_security_event(db, user, request, "mfa.disabled", "warning")
    db.commit()
    return {"message": "MFA desativado"}


@router.get("/security/events")
def security_events(user: User = Depends(require_permission("audit.view")), db: Session = Depends(get_db)):
    rows = db.scalars(select(SecurityEvent).where(SecurityEvent.company_id == user.company_id, SecurityEvent.deleted_at.is_(None)).order_by(SecurityEvent.created_at.desc()).limit(100))
    return [{"id": item.id, "event_type": item.event_type, "severity": item.severity, "ip_address": item.ip_address, "detail": from_json(item.detail_json, {}), "created_at": item.created_at} for item in rows]
