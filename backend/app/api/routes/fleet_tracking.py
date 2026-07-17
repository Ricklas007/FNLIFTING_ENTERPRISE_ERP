import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_permission
from app.core.security import hash_password
from app.database.session import get_db
from app.models import FleetAlert, FleetAlertRule, Geofence, GPSPosition, GPSTrackerDevice, Truck, User
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
    GPSReplayOut,
    GPSTrackerDeviceCreate,
    GPSTrackerDeviceOut,
    GPSTrackerDeviceWithToken,
)
from app.services.enterprise_utils import now_utc, to_json
from app.services.gps_tracking_service import (
    alert_out,
    device_token,
    geojson_payload,
    geofence_out,
    record_gps_ingest,
    replay_payload,
    rule_out,
    tracker_device_out,
    verify_tracker_token,
)


router = APIRouter(prefix="/fleet", tags=["GPS, Geofences e Alertas"])


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
