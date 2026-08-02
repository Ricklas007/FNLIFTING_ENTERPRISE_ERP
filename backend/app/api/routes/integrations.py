import base64
import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.api.routes import maps
from app.core.security import hash_password
from app.database.session import get_db
from app.models import GPSTrackerDevice, Truck, User
from app.services.enterprise_utils import to_json


router = APIRouter(prefix="/integrations", tags=["Integrações externas"])


class TraccarStatusOut(BaseModel):
    provider: str = "TRACCAR"
    status: str
    configured: bool
    base_url: str | None = None
    message: str
    checked_at: datetime


class TraccarDeviceOut(BaseModel):
    external_id: str
    name: str
    unique_id: str | None = None
    status: str | None = None
    phone: str | None = None
    model: str | None = None
    category: str | None = None
    last_update: str | None = None


class TraccarImportRequest(BaseModel):
    device_ids: list[str] = Field(default_factory=list)


class TraccarLinkRequest(BaseModel):
    device_id: str
    truck_id: str


@router.post("/serpapi/test", response_model=maps.SerpApiStatus)
def serpapi_test(request: Request, user: User = Depends(require_permission("settings.manage")), db: Session = Depends(get_db)):
    try:
        maps._check_serpapi_rate(f"serpapi-test:{user.id}")
    except HTTPException as exc:
        snapshot = maps.serpapi_status_snapshot()
        result = maps.SerpApiStatus(
            status="RATE_LIMITED",
            configured=snapshot.configured,
            enabled=snapshot.enabled,
            base_url=snapshot.base_url,
            message=str(exc.detail),
            checked_at=datetime.now(timezone.utc),
            cache_ttl_seconds=snapshot.cache_ttl_seconds,
            rate_limit_per_minute=snapshot.rate_limit_per_minute,
            last_success_at=snapshot.last_success_at,
            last_error=str(exc.detail),
            metrics=snapshot.metrics,
        )
        maps.audit_serpapi_event(db, request, user, "test", "Teste SerpApi bloqueado por rate limit local", {"status": result.status})
        db.commit()
        return result
    result = maps.serpapi_health_check()
    maps.audit_serpapi_event(db, request, user, "test", "Teste SerpApi executado", {"status": result.status, "configured": result.configured, "enabled": result.enabled})
    db.commit()
    return result


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _traccar_config() -> tuple[bool, str, float]:
    enabled = _truthy(os.getenv("TRACCAR_ENABLED"))
    base_url = (os.getenv("TRACCAR_BASE_URL") or os.getenv("TRACCAR_URL") or "").strip().rstrip("/")
    timeout = float(os.getenv("TRACCAR_TIMEOUT", "8"))
    return bool(enabled and base_url), base_url, timeout


def _traccar_request(path: str, query: dict[str, Any] | None = None) -> UrlRequest:
    configured, base_url, _ = _traccar_config()
    if not configured:
        raise HTTPException(status_code=503, detail="Traccar não configurado. Defina TRACCAR_ENABLED=true e TRACCAR_BASE_URL/TRACCAR_URL no backend.")
    url = f"{base_url}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    request = UrlRequest(url, headers={"Accept": "application/json", "User-Agent": "FNLIFTING-ERP/0.12.1"})
    token = os.getenv("TRACCAR_TOKEN", "").strip()
    username = os.getenv("TRACCAR_USERNAME", "").strip()
    password = os.getenv("TRACCAR_PASSWORD", "").strip()
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    elif username and password:
        raw = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        request.add_header("Authorization", f"Basic {raw}")
    return request


def _traccar_json(path: str, query: dict[str, Any] | None = None) -> Any:
    _, _, timeout = _traccar_config()
    try:
        with urlopen(_traccar_request(path, query), timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise HTTPException(status_code=502, detail="Traccar recusou as credenciais/token configurados.") from exc
        raise HTTPException(status_code=502, detail=f"Traccar respondeu HTTP {exc.code}.") from exc
    except (TimeoutError, URLError) as exc:
        raise HTTPException(status_code=504, detail="Timeout ao contactar Traccar.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Resposta Traccar inválida.") from exc


def _normalize_device(item: dict[str, Any]) -> TraccarDeviceOut:
    return TraccarDeviceOut(
        external_id=str(item.get("id")),
        name=str(item.get("name") or item.get("uniqueId") or "Tracker Traccar"),
        unique_id=item.get("uniqueId"),
        status=item.get("status"),
        phone=item.get("phone"),
        model=item.get("model"),
        category=item.get("category"),
        last_update=item.get("lastUpdate"),
    )


@router.get("/traccar/status", response_model=TraccarStatusOut)
def traccar_status(user: User = Depends(require_permission("fleet.view"))):
    configured, base_url, _ = _traccar_config()
    checked_at = datetime.now(timezone.utc)
    if not configured:
        return TraccarStatusOut(status="DISCONNECTED", configured=False, base_url=None, message="Traccar não configurado.", checked_at=checked_at)
    try:
        _traccar_json("/api/server")
        return TraccarStatusOut(status="CONNECTED", configured=True, base_url=base_url, message="Ligação Traccar validada.", checked_at=checked_at)
    except HTTPException as exc:
        status_value = "AUTH_ERROR" if exc.status_code == 502 and "credenciais" in str(exc.detail).lower() else "DISCONNECTED"
        return TraccarStatusOut(status=status_value, configured=True, base_url=base_url, message=str(exc.detail), checked_at=checked_at)


@router.post("/traccar/test", response_model=TraccarStatusOut)
def traccar_test(user: User = Depends(require_permission("fleet.manage"))):
    return traccar_status(user)


@router.get("/traccar/devices", response_model=list[TraccarDeviceOut])
def traccar_devices(user: User = Depends(require_permission("fleet.view"))):
    payload = _traccar_json("/api/devices")
    if not isinstance(payload, list):
        raise HTTPException(status_code=502, detail="Resposta Traccar de devices inválida.")
    return [_normalize_device(item) for item in payload if isinstance(item, dict)]


@router.post("/traccar/import-devices", response_model=list[TraccarDeviceOut], status_code=status.HTTP_201_CREATED)
def traccar_import_devices(payload: TraccarImportRequest, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    devices = traccar_devices(user)
    selected = [item for item in devices if not payload.device_ids or item.external_id in payload.device_ids]
    for item in selected:
        existing = db.scalar(select(GPSTrackerDevice).where(GPSTrackerDevice.company_id == user.company_id, GPSTrackerDevice.device_uid == (item.unique_id or item.external_id)))
        if existing:
            existing.label = item.name
            existing.provider = "TRACCAR"
            existing.capabilities_json = to_json(["gps", "events", "status", "traccar"])
            continue
        db.add(GPSTrackerDevice(
            company_id=user.company_id,
            device_uid=item.unique_id or item.external_id,
            label=item.name,
            provider="TRACCAR",
            token_hash=hash_password(uuid4().hex),
            capabilities_json=to_json(["gps", "events", "status", "traccar"]),
            status="active" if item.status != "disabled" else "inactive",
            created_by=user.id,
        ))
    db.commit()
    return selected


@router.post("/traccar/link-device", response_model=TraccarDeviceOut)
def traccar_link_device(payload: TraccarLinkRequest, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    truck = db.scalar(select(Truck).where(Truck.id == payload.truck_id, Truck.company_id == user.company_id, Truck.deleted_at.is_(None)))
    if not truck:
        raise HTTPException(status_code=404, detail="Camião não encontrado.")
    device = db.scalar(select(GPSTrackerDevice).where(GPSTrackerDevice.id == payload.device_id, GPSTrackerDevice.company_id == user.company_id, GPSTrackerDevice.deleted_at.is_(None)))
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo GPS não encontrado.")
    device.truck_id = truck.id
    device.provider = "TRACCAR"
    device.updated_by = user.id
    db.commit()
    return TraccarDeviceOut(external_id=device.id, name=device.label, unique_id=device.device_uid, status=device.status)
