import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_permission
from app.core.security import hash_password
from app.database.session import get_db
from app.models import FleetAlert, FleetAlertRule, Geofence, GPSPosition, GPSTrackerDevice, OperationalPlace, Truck, User
from app.schemas.auth import MessageResponse
from app.schemas.fleet import GPSPositionOut
from app.schemas.fleet_tracking import (
    DeviceIngestOut,
    FleetAlertOut,
    FleetAlertRuleCreate,
    FleetAlertRuleOut,
    GeofenceCreate,
    GeofenceOut,
    GeofenceUpdate,
    GPSDeviceIngestRequest,
    GPSPilotChecklistOut,
    GPSPilotSimulationOut,
    GPSPilotSimulationRequest,
    GPSProviderHealthOut,
    GPSProviderOut,
    GPSReplayOut,
    GPSTrackerDeviceCreate,
    GPSTrackerDeviceOut,
    GPSTrackerDeviceWithToken,
    OperationalPlaceCreate,
    OperationalPlaceOut,
    OperationalPlaceUpdate,
)
from app.services.enterprise_utils import now_utc, to_json
from app.services.gps_pilot_service import gps_pilot_report_path, onboarding_checklist_payload, simulate_gps_pilot
from app.services.gps_tracking_service import (
    alert_out,
    device_token,
    geojson_payload,
    geofence_out,
    operational_place_out,
    record_gps_ingest,
    replay_payload,
    rule_out,
    tracker_device_out,
    verify_tracker_token,
)


router = APIRouter(prefix="/fleet", tags=["GPS, Geofences e Alertas"])


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _gps_provider_registry() -> list[dict[str, object]]:
    traccar_url = os.getenv("TRACCAR_URL", "").strip()
    traccar_enabled = _truthy(os.getenv("TRACCAR_ENABLED"))
    vendor_url = os.getenv("GPS_VENDOR_API_URL", "").strip()
    mqtt_url = os.getenv("GPS_MQTT_URL", "").strip()
    return [
        {
            "code": "TRACCAR",
            "name": "Traccar Gateway",
            "provider_type": "telematics_gateway",
            "status": "CONFIGURED_NOT_TESTED" if traccar_enabled and traccar_url else "DISCONNECTED",
            "requires_credentials": True,
            "configured": bool(traccar_enabled and traccar_url),
            "capabilities": ["devices", "positions", "events", "status", "websocket"],
            "notes": "Defina TRACCAR_ENABLED=true, TRACCAR_URL e credenciais/token para testar ligação real.",
        },
        {
            "code": "VENDOR_CLOUD",
            "name": "Fornecedor cloud do fabricante",
            "provider_type": "vendor_api",
            "status": "CONFIGURED_NOT_TESTED" if vendor_url else "DISCONNECTED",
            "requires_credentials": True,
            "configured": bool(vendor_url),
            "capabilities": ["devices", "positions", "events"],
            "notes": "O IMEI/serial identifica o rastreador; autenticação real depende da API do fabricante.",
        },
        {
            "code": "HTTP_TRACKER",
            "name": "HTTP tracker tokenizado",
            "provider_type": "direct_http",
            "status": "CONNECTED",
            "requires_credentials": False,
            "configured": True,
            "capabilities": ["secure_ingest", "idempotency", "tenant_validation"],
            "notes": "Endpoint /fleet/gps/ingest usa X-GPS-Device-Token; não usa login humano.",
        },
        {
            "code": "MQTT_TRACKER",
            "name": "MQTT tracker",
            "provider_type": "mqtt",
            "status": "CONFIGURED_NOT_TESTED" if mqtt_url else "DISCONNECTED",
            "requires_credentials": True,
            "configured": bool(mqtt_url),
            "capabilities": ["positions", "events", "heartbeat"],
            "notes": "Adapter preparado no registry; broker real ainda precisa de configuração e worker.",
        },
        {
            "code": "MANUAL_IMPORT",
            "name": "Importação manual GPX/CSV/GeoJSON",
            "provider_type": "manual_import",
            "status": "CONFIGURED_NOT_TESTED",
            "requires_credentials": False,
            "configured": True,
            "capabilities": ["history", "replay"],
            "notes": "Provider de recuperação/histórico; não representa tempo real.",
        },
    ]


def _traccar_health() -> tuple[str, str, bool]:
    url = os.getenv("TRACCAR_URL", "").strip().rstrip("/")
    enabled = _truthy(os.getenv("TRACCAR_ENABLED"))
    if not enabled or not url:
        return "DISCONNECTED", "TRACCAR_ENABLED/TRACCAR_URL não configurados.", False
    request = urllib.request.Request(f"{url}/api/server", method="GET")
    token = os.getenv("TRACCAR_TOKEN", "").strip()
    username = os.getenv("TRACCAR_USERNAME", "").strip()
    password = os.getenv("TRACCAR_PASSWORD", "").strip()
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    elif username and password:
        import base64

        raw = f"{username}:{password}".encode("utf-8")
        request.add_header("Authorization", f"Basic {base64.b64encode(raw).decode('ascii')}")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if 200 <= response.status < 300:
                return "CONNECTED", "Ligação Traccar validada sem expor credenciais.", True
            return "DISCONNECTED", f"Traccar respondeu HTTP {response.status}.", True
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return "AUTH_ERROR", "Traccar recusou as credenciais/token configurados.", True
        return "DISCONNECTED", f"Traccar respondeu HTTP {exc.code}.", True
    except Exception as exc:
        return "DISCONNECTED", f"Falha ao contactar Traccar: {exc.__class__.__name__}", True


def _commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


def _validate_truck(db: Session, company_id: str, truck_id: str | None) -> None:
    if not truck_id:
        return
    exists = db.scalar(select(Truck.id).where(Truck.id == truck_id, Truck.company_id == company_id, Truck.deleted_at.is_(None)))
    if not exists:
        raise HTTPException(status_code=404, detail="Camião não encontrado")


def _validate_geometry(payload: GeofenceCreate | GeofenceUpdate, current: Geofence | None = None) -> tuple[str, str, float | None]:
    shape = payload.shape_type or (current.shape_type if current else "circle")
    radius = payload.radius_meters if payload.radius_meters is not None else (current.radius_meters if current else None)
    geometry = payload.geometry if payload.geometry is not None else (json.loads(current.geometry_json) if current else {})
    if shape in {"circle", "point"}:
        center = geometry.get("center") or geometry.get("coordinates")
        if not isinstance(center, list) or len(center) < 2:
            raise HTTPException(status_code=422, detail="Geofence circular exige center/coordinates [longitude, latitude]")
        if shape == "circle" and not (radius or geometry.get("radius_meters")):
            raise HTTPException(status_code=422, detail="Geofence circular exige radius_meters")
    if shape in {"polygon", "corridor"}:
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates[0] if coordinates and isinstance(coordinates[0], list) and coordinates[0] and isinstance(coordinates[0][0], list) else coordinates) < 3:
            raise HTTPException(status_code=422, detail="Geofence poligonal/corredor exige pelo menos 3 coordenadas")
    return shape, json.dumps(geometry, ensure_ascii=False), radius


def _geofence_type_for_place(category: str | None, title: str) -> str:
    value = f"{category or ''} {title}".lower()
    if "combust" in value or "gas" in value or "fuel" in value:
        return "FUEL_STATION"
    if "terminal" in value or "porto" in value or "log" in value:
        return "TERMINAL"
    if "cliente" in value or "customer" in value:
        return "CLIENT"
    if "base" in value or "depot" in value:
        return "BASE"
    return "CHECKPOINT"


def _create_place_geofence(db: Session, payload: OperationalPlaceCreate, user: User) -> Geofence:
    geofence_type = payload.geofence_type or _geofence_type_for_place(payload.category, payload.title)
    geometry = {
        "center": [payload.longitude, payload.latitude],
        "source": payload.source,
        "external_id": payload.external_id,
        "address": payload.address,
        "category": payload.category,
        "retrieved_at": payload.retrieved_at.isoformat() if payload.retrieved_at else None,
    }
    record = Geofence(
        company_id=user.company_id,
        name=payload.title,
        geofence_type=geofence_type,
        shape_type="point",
        geometry_json=json.dumps(geometry, ensure_ascii=False),
        radius_meters=payload.radius_meters,
        alert_on_enter=True,
        alert_on_exit=False,
        status="active",
        created_by=user.id,
    )
    db.add(record)
    db.flush()
    return record


def _position_query(company_id: str, truck_id: str | None, trip_id: str | None, date_from: datetime | None, date_to: datetime | None):
    query = select(GPSPosition).options(selectinload(GPSPosition.truck).selectinload(Truck.driver)).where(
        GPSPosition.company_id == company_id,
        GPSPosition.deleted_at.is_(None),
    )
    if truck_id:
        query = query.where(GPSPosition.truck_id == truck_id)
    if trip_id:
        query = query.where(GPSPosition.trip_id == trip_id)
    if date_from:
        query = query.where(GPSPosition.recorded_at >= date_from)
    if date_to:
        query = query.where(GPSPosition.recorded_at <= date_to)
    return query.order_by(GPSPosition.recorded_at.asc())




@router.get("/gps/pilot/checklist", response_model=GPSPilotChecklistOut)
def gps_pilot_checklist(user: User = Depends(require_permission("fleet.view"))):
    return onboarding_checklist_payload()


@router.post("/gps/pilot/simulate", response_model=GPSPilotSimulationOut, status_code=status.HTTP_201_CREATED)
def run_gps_pilot_simulation(payload: GPSPilotSimulationRequest, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    return simulate_gps_pilot(db, user, run_code=payload.run_code, include_report=payload.include_report)


@router.get("/gps/pilot/reports/{filename}")
def download_gps_pilot_report(filename: str, user: User = Depends(require_permission("fleet.view"))):
    path = gps_pilot_report_path(filename)
    return FileResponse(path, media_type="application/pdf", filename=path.name)

@router.get("/gps/providers", response_model=list[GPSProviderOut])
def list_gps_providers(user: User = Depends(require_permission("fleet.view"))):
    return _gps_provider_registry()


@router.post("/gps/providers/{provider_code}/health", response_model=GPSProviderHealthOut)
def gps_provider_health(provider_code: str, user: User = Depends(require_permission("fleet.manage"))):
    code = provider_code.strip().upper()
    if code == "TRACCAR":
        status_value, message, configured = _traccar_health()
    else:
        provider = next((item for item in _gps_provider_registry() if item["code"] == code), None)
        if not provider:
          raise HTTPException(status_code=404, detail="Provider GPS não encontrado")
        status_value = str(provider["status"])
        configured = bool(provider["configured"])
        message = str(provider.get("notes") or "Provider registado, mas sem teste ativo implementado.")
    return GPSProviderHealthOut(code=code, status=status_value, message=message, configured=configured, tested_at=now_utc())


@router.get("/gps/devices", response_model=list[GPSTrackerDeviceOut])
def list_gps_devices(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    rows = db.scalars(select(GPSTrackerDevice).where(GPSTrackerDevice.company_id == user.company_id, GPSTrackerDevice.deleted_at.is_(None)).order_by(GPSTrackerDevice.created_at.desc())).all()
    return [tracker_device_out(row) for row in rows]


@router.post("/gps/devices", response_model=GPSTrackerDeviceWithToken, status_code=status.HTTP_201_CREATED)
def create_gps_device(payload: GPSTrackerDeviceCreate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    _validate_truck(db, user.company_id, payload.truck_id)
    record = GPSTrackerDevice(
        company_id=user.company_id,
        truck_id=payload.truck_id,
        driver_id=payload.driver_id,
        device_uid=payload.device_uid,
        label=payload.label,
        provider=payload.provider,
        token_hash=hash_password("pending"),
        capabilities_json=to_json(payload.capabilities),
        status=payload.status,
        created_by=user.id,
    )
    db.add(record)
    db.flush()
    token, secret = device_token(record.id)
    record.token_hash = hash_password(secret)
    _commit_or_conflict(db, "Dispositivo GPS já registado para esta empresa")
    db.refresh(record)
    return tracker_device_out(record, token)


@router.post("/gps/devices/{device_id}/rotate-token", response_model=GPSTrackerDeviceWithToken)
def rotate_gps_device_token(device_id: str, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = db.scalar(select(GPSTrackerDevice).where(GPSTrackerDevice.id == device_id, GPSTrackerDevice.company_id == user.company_id, GPSTrackerDevice.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Dispositivo GPS não encontrado")
    token, secret = device_token(record.id)
    record.token_hash = hash_password(secret)
    record.updated_by = user.id
    db.commit()
    return tracker_device_out(record, token)


@router.post("/gps/ingest", response_model=DeviceIngestOut, status_code=status.HTTP_201_CREATED)
def ingest_gps_from_device(
    payload: GPSDeviceIngestRequest,
    request: Request,
    x_gps_device_token: Annotated[str | None, Header(alias="X-GPS-Device-Token")] = None,
    db: Session = Depends(get_db),
):
    device = verify_tracker_token(db, x_gps_device_token)
    truck_id = payload.truck_id or device.truck_id
    result = record_gps_ingest(
        db,
        company_id=device.company_id,
        created_by=None,
        provider=device.provider,
        event_id=payload.event_id,
        truck_id=truck_id,
        trip_id=payload.trip_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        speed_kmh=payload.speed_kmh,
        heading=payload.heading,
        fuel_level_percent=payload.fuel_level_percent,
        vehicle_state=payload.vehicle_state,
        recorded_at=payload.timestamp,
        payload={
            **payload.payload,
            "device_id": device.id,
            "device_uid": device.device_uid,
            "driver_id": payload.driver_id or device.driver_id,
            "accuracy_meters": payload.accuracy_meters,
            "ignition_status": payload.ignition_status,
            "odometer_km": payload.odometer_km,
        },
    )
    device.last_seen_at = now_utc()
    device.last_ip = request.client.host if request.client else None
    db.commit()
    return result


@router.get("/gps/history", response_model=list[GPSPositionOut])
def gps_history(
    truck_id: str | None = None,
    trip_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=1000, ge=1, le=5000),
    user: User = Depends(require_permission("fleet.view")),
    db: Session = Depends(get_db),
):
    return list(db.scalars(_position_query(user.company_id, truck_id, trip_id, date_from, date_to).limit(limit)).unique().all())


@router.get("/gps/replay", response_model=GPSReplayOut)
def gps_replay(
    truck_id: str | None = None,
    trip_id: str | None = None,
    limit: int = Query(default=1000, ge=2, le=5000),
    user: User = Depends(require_permission("fleet.view")),
    db: Session = Depends(get_db),
):
    if not truck_id and not trip_id:
        raise HTTPException(status_code=422, detail="Informe truck_id ou trip_id para replay")
    positions = list(db.scalars(_position_query(user.company_id, truck_id, trip_id, None, None).limit(limit)).unique().all())
    return replay_payload(positions)


@router.get("/gps/export.geojson")
def gps_export_geojson(
    truck_id: str | None = None,
    trip_id: str | None = None,
    limit: int = Query(default=2000, ge=2, le=10000),
    user: User = Depends(require_permission("fleet.view")),
    db: Session = Depends(get_db),
):
    if not truck_id and not trip_id:
        raise HTTPException(status_code=422, detail="Informe truck_id ou trip_id para exportar")
    positions = list(db.scalars(_position_query(user.company_id, truck_id, trip_id, None, None).limit(limit)).unique().all())
    payload = geojson_payload(positions)
    return payload


@router.get("/gps/stream")
def gps_stream(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    positions = list(db.scalars(_position_query(user.company_id, None, None, None, None).limit(250)).unique().all())
    payload = json.dumps(jsonable_encoder({"type": "gps_live", "positions": replay_payload(positions)["positions"]}), ensure_ascii=False)
    return StreamingResponse(iter([f"event: gps_live\ndata: {payload}\n\n"]), media_type="text/event-stream")


@router.get("/geofences", response_model=list[GeofenceOut])
def list_geofences(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Geofence).where(Geofence.company_id == user.company_id, Geofence.deleted_at.is_(None)).order_by(Geofence.name)).all()
    return [geofence_out(row) for row in rows]


@router.get("/operational-places", response_model=list[OperationalPlaceOut])
def list_operational_places(
    status_filter: str = Query(default="active", alias="status", pattern="^(active|inactive|archived|all)$"),
    category: str | None = Query(default=None, max_length=80),
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=200, ge=1, le=1000),
    user: User = Depends(require_permission("fleet.view")),
    db: Session = Depends(get_db),
):
    query = select(OperationalPlace).where(
        OperationalPlace.company_id == user.company_id,
        OperationalPlace.deleted_at.is_(None),
    )
    if status_filter != "all":
        query = query.where(OperationalPlace.status == status_filter)
    if category:
        query = query.where(OperationalPlace.category == category)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(OperationalPlace.title.ilike(like))
    rows = db.scalars(query.order_by(OperationalPlace.title.asc()).limit(limit)).all()
    return [operational_place_out(row) for row in rows]


@router.post("/operational-places", response_model=OperationalPlaceOut, status_code=status.HTTP_201_CREATED)
def create_operational_place(payload: OperationalPlaceCreate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = None
    if payload.external_id:
        record = db.scalar(
            select(OperationalPlace).where(
                OperationalPlace.company_id == user.company_id,
                OperationalPlace.source == payload.source,
                OperationalPlace.external_id == payload.external_id,
                OperationalPlace.deleted_at.is_(None),
            )
        )
    if record is None:
        record = OperationalPlace(
            company_id=user.company_id,
            title=payload.title,
            category=payload.category,
            address=payload.address,
            phone=payload.phone,
            website=payload.website,
            latitude=payload.latitude,
            longitude=payload.longitude,
            source=payload.source,
            external_id=payload.external_id,
            status=payload.status,
            metadata_json=to_json(payload.metadata),
            retrieved_at=payload.retrieved_at,
            created_by=user.id,
        )
        db.add(record)
    else:
        record.title = payload.title
        record.category = payload.category
        record.address = payload.address
        record.phone = payload.phone
        record.website = payload.website
        record.latitude = payload.latitude
        record.longitude = payload.longitude
        record.status = payload.status
        record.metadata_json = to_json(payload.metadata)
        record.retrieved_at = payload.retrieved_at
        record.updated_by = user.id
    if payload.create_geofence and not record.geofence_id:
        geofence = _create_place_geofence(db, payload, user)
        record.geofence_id = geofence.id
    _commit_or_conflict(db, "Local operacional já registado para esta fonte")
    db.refresh(record)
    return operational_place_out(record)


@router.patch("/operational-places/{place_id}", response_model=OperationalPlaceOut)
def update_operational_place(place_id: str, payload: OperationalPlaceUpdate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = db.scalar(select(OperationalPlace).where(OperationalPlace.id == place_id, OperationalPlace.company_id == user.company_id, OperationalPlace.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Local operacional não encontrado")
    changes = payload.model_dump(exclude_unset=True, exclude={"metadata"})
    for field, value in changes.items():
        setattr(record, field, value)
    if payload.metadata is not None:
        record.metadata_json = to_json(payload.metadata)
    record.updated_by = user.id
    db.commit()
    db.refresh(record)
    return operational_place_out(record)


@router.post("/geofences", response_model=GeofenceOut, status_code=status.HTTP_201_CREATED)
def create_geofence(payload: GeofenceCreate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    shape, geometry_json, radius = _validate_geometry(payload)
    record = Geofence(
        company_id=user.company_id,
        name=payload.name,
        geofence_type=payload.geofence_type,
        shape_type=shape,
        geometry_json=geometry_json,
        radius_meters=radius or payload.geometry.get("radius_meters"),
        alert_on_enter=payload.alert_on_enter,
        alert_on_exit=payload.alert_on_exit,
        dwell_minutes=payload.dwell_minutes,
        status=payload.status,
        created_by=user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return geofence_out(record)


@router.patch("/geofences/{geofence_id}", response_model=GeofenceOut)
def update_geofence(geofence_id: str, payload: GeofenceUpdate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = db.scalar(select(Geofence).where(Geofence.id == geofence_id, Geofence.company_id == user.company_id, Geofence.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Geofence não encontrada")
    changes = payload.model_dump(exclude_unset=True, exclude={"geometry", "shape_type", "radius_meters"})
    for field, value in changes.items():
        setattr(record, field, value)
    if payload.geometry is not None or payload.shape_type is not None or payload.radius_meters is not None:
        shape, geometry_json, radius = _validate_geometry(payload, record)
        record.shape_type = shape
        record.geometry_json = geometry_json
        record.radius_meters = radius
    record.updated_by = user.id
    db.commit()
    return geofence_out(record)


@router.get("/alert-rules", response_model=list[FleetAlertRuleOut])
def list_alert_rules(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    rows = db.scalars(select(FleetAlertRule).where(FleetAlertRule.company_id == user.company_id, FleetAlertRule.deleted_at.is_(None)).order_by(FleetAlertRule.code)).all()
    return [rule_out(row) for row in rows]


@router.post("/alert-rules", response_model=FleetAlertRuleOut, status_code=status.HTTP_201_CREATED)
def create_alert_rule(payload: FleetAlertRuleCreate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = FleetAlertRule(
        company_id=user.company_id,
        code=payload.code,
        name=payload.name,
        alert_type=payload.alert_type,
        severity=payload.severity,
        condition_json=to_json(payload.condition),
        status=payload.status,
        created_by=user.id,
    )
    db.add(record)
    _commit_or_conflict(db, "Regra de alerta já existe")
    db.refresh(record)
    return rule_out(record)


@router.get("/alerts", response_model=list[FleetAlertOut])
def list_fleet_alerts(
    status_filter: str = Query(default="open", alias="status"),
    user: User = Depends(require_permission("fleet.view")),
    db: Session = Depends(get_db),
):
    query = select(FleetAlert).where(FleetAlert.company_id == user.company_id, FleetAlert.deleted_at.is_(None)).order_by(FleetAlert.triggered_at.desc()).limit(200)
    if status_filter:
        query = query.where(FleetAlert.status == status_filter)
    return [alert_out(row) for row in db.scalars(query).all()]


@router.post("/alerts/{alert_id}/resolve", response_model=MessageResponse)
def resolve_fleet_alert(alert_id: str, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = db.scalar(select(FleetAlert).where(FleetAlert.id == alert_id, FleetAlert.company_id == user.company_id, FleetAlert.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    record.status = "resolved"
    record.resolved_at = datetime.now(timezone.utc)
    record.updated_by = user.id
    db.commit()
    return MessageResponse(message="Alerta resolvido")
