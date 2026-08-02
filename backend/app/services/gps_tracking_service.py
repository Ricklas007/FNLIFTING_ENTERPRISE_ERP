from __future__ import annotations

import json
import math
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import (
    FleetAlert,
    FleetAlertRule,
    FleetCommand,
    Geofence,
    GeofenceEvent,
    GPSIntegrationEvent,
    GPSPosition,
    GPSTrackerDevice,
    OperationalPlace,
    Trip,
    Truck,
)
from app.services.enterprise_utils import from_json, now_utc, to_json
from app.services.notification_service import create_notification


def _loads(value: str | None, default: Any) -> Any:
    return from_json(value, default)


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _point_in_polygon(latitude: float, longitude: float, coordinates: list[list[float]]) -> bool:
    inside = False
    if len(coordinates) < 3:
        return False
    x, y = longitude, latitude
    j = len(coordinates) - 1
    for i, point in enumerate(coordinates):
        xi, yi = point[0], point[1]
        xj, yj = coordinates[j][0], coordinates[j][1]
        intersects = ((yi > y) != (yj > y)) and (x < ((xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi))
        if intersects:
            inside = not inside
        j = i
    return inside


def point_inside_geofence(latitude: float, longitude: float, geofence: Geofence) -> bool:
    geometry = _loads(geofence.geometry_json, {})
    shape = geofence.shape_type
    if shape in {"circle", "point"}:
        center = geometry.get("center") or geometry.get("coordinates")
        if not isinstance(center, list) or len(center) < 2:
            return False
        radius = geofence.radius_meters or geometry.get("radius_meters") or (75 if shape == "point" else 0)
        return _distance_meters(latitude, longitude, float(center[1]), float(center[0])) <= float(radius)
    if shape in {"polygon", "corridor"}:
        coordinates = geometry.get("coordinates", [])
        if coordinates and isinstance(coordinates[0], list) and coordinates[0] and isinstance(coordinates[0][0], list):
            coordinates = coordinates[0]
        return _point_in_polygon(latitude, longitude, coordinates)
    return False


def device_token(device_id: str) -> tuple[str, str]:
    secret = secrets.token_urlsafe(32)
    return f"fnlgps.{device_id}.{secret}", secret


def verify_tracker_token(db: Session, token: str | None) -> GPSTrackerDevice:
    if not token:
        raise HTTPException(status_code=401, detail="Token GPS ausente")
    parts = token.split(".", 2)
    if len(parts) != 3 or parts[0] != "fnlgps":
        raise HTTPException(status_code=401, detail="Token GPS inválido")
    device = db.scalar(select(GPSTrackerDevice).where(GPSTrackerDevice.id == parts[1], GPSTrackerDevice.deleted_at.is_(None)))
    if not device or device.status != "active" or not verify_password(parts[2], device.token_hash):
        raise HTTPException(status_code=401, detail="Dispositivo GPS não autorizado")
    return device


def tracker_device_out(device: GPSTrackerDevice, token: str | None = None) -> dict[str, Any]:
    payload = {
        "id": device.id,
        "device_uid": device.device_uid,
        "label": device.label,
        "truck_id": device.truck_id,
        "driver_id": device.driver_id,
        "provider": device.provider,
        "capabilities": _loads(device.capabilities_json, []),
        "status": device.status,
        "last_seen_at": device.last_seen_at,
        "created_at": device.created_at,
    }
    if token:
        payload["token"] = token
    return payload


def geofence_out(record: Geofence) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "geofence_type": record.geofence_type,
        "shape_type": record.shape_type,
        "geometry": _loads(record.geometry_json, {}),
        "radius_meters": record.radius_meters,
        "alert_on_enter": record.alert_on_enter,
        "alert_on_exit": record.alert_on_exit,
        "dwell_minutes": record.dwell_minutes,
        "status": record.status,
        "created_at": record.created_at,
    }


def operational_place_out(record: OperationalPlace) -> dict[str, Any]:
    return {
        "id": record.id,
        "title": record.title,
        "category": record.category,
        "address": record.address,
        "phone": record.phone,
        "website": record.website,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "source": record.source,
        "external_id": record.external_id,
        "geofence_id": record.geofence_id,
        "status": record.status,
        "metadata": _loads(record.metadata_json, {}),
        "retrieved_at": record.retrieved_at,
        "created_at": record.created_at,
    }


def alert_out(record: FleetAlert) -> dict[str, Any]:
    return {
        "id": record.id,
        "truck_id": record.truck_id,
        "trip_id": record.trip_id,
        "alert_type": record.alert_type,
        "severity": record.severity,
        "title": record.title,
        "message": record.message,
        "status": record.status,
        "triggered_at": record.triggered_at,
        "resolved_at": record.resolved_at,
        "payload": _loads(record.payload_json, {}),
    }


def rule_out(record: FleetAlertRule) -> dict[str, Any]:
    return {
        "id": record.id,
        "code": record.code,
        "name": record.name,
        "alert_type": record.alert_type,
        "severity": record.severity,
        "condition": _loads(record.condition_json, {}),
        "status": record.status,
        "created_at": record.created_at,
    }


def _existing_event(db: Session, company_id: str, provider: str, event_id: str) -> GPSIntegrationEvent | None:
    return db.scalar(
        select(GPSIntegrationEvent).where(
            GPSIntegrationEvent.company_id == company_id,
            GPSIntegrationEvent.provider == provider,
            GPSIntegrationEvent.payload_json.contains(event_id),
            GPSIntegrationEvent.deleted_at.is_(None),
        )
    )


def _speed_threshold(db: Session, company_id: str) -> tuple[float, FleetAlertRule | None]:
    rule = db.scalar(
        select(FleetAlertRule)
        .where(FleetAlertRule.company_id == company_id, FleetAlertRule.alert_type == "speeding", FleetAlertRule.status == "active", FleetAlertRule.deleted_at.is_(None))
        .order_by(FleetAlertRule.created_at.desc())
    )
    if not rule:
        return 90.0, None
    condition = _loads(rule.condition_json, {})
    return float(condition.get("max_speed_kmh", 90)), rule


def _create_alert(
    db: Session,
    *,
    company_id: str,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    dedupe_key: str,
    truck_id: str | None,
    trip_id: str | None,
    payload: dict[str, Any],
    created_by: str | None,
    rule_id: str | None = None,
    geofence_event_id: str | None = None,
) -> FleetAlert | None:
    existing = db.scalar(select(FleetAlert).where(FleetAlert.company_id == company_id, FleetAlert.dedupe_key == dedupe_key, FleetAlert.deleted_at.is_(None)))
    if existing:
        return None
    alert = FleetAlert(
        company_id=company_id,
        rule_id=rule_id,
        geofence_event_id=geofence_event_id,
        truck_id=truck_id,
        trip_id=trip_id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        dedupe_key=dedupe_key,
        payload_json=to_json(payload),
        status="open",
        triggered_at=now_utc(),
        created_by=created_by,
    )
    db.add(alert)
    command_type = "speeding_alert" if alert_type == "speeding" else alert_type
    db.add(
        FleetCommand(
            company_id=company_id,
            truck_id=truck_id,
            trip_id=trip_id,
            command_type=command_type,
            priority="critical" if severity == "critical" else "high" if severity == "warning" else "normal",
            payload_json=to_json({"alert": title, **payload}),
            status="open",
            created_by=created_by,
        )
    )
    create_notification(db, company_id, title, message, severity, created_by=created_by, dedupe_key=dedupe_key)
    return alert


def _latest_previous_position(db: Session, company_id: str, truck_id: str, recorded_at: datetime) -> GPSPosition | None:
    return db.scalar(
        select(GPSPosition)
        .where(
            GPSPosition.company_id == company_id,
            GPSPosition.truck_id == truck_id,
            GPSPosition.recorded_at < recorded_at,
            GPSPosition.deleted_at.is_(None),
        )
        .order_by(GPSPosition.recorded_at.desc())
    )


def evaluate_geofences(
    db: Session,
    *,
    company_id: str,
    truck_id: str | None,
    trip_id: str | None,
    latitude: float,
    longitude: float,
    recorded_at: datetime,
    event_id: str,
    created_by: str | None,
) -> tuple[int, int]:
    if not truck_id:
        return 0, 0
    previous = _latest_previous_position(db, company_id, truck_id, recorded_at)
    geofence_events = 0
    alerts = 0
    geofences = db.scalars(select(Geofence).where(Geofence.company_id == company_id, Geofence.status == "active", Geofence.deleted_at.is_(None))).all()
    for geofence in geofences:
        inside_now = point_inside_geofence(latitude, longitude, geofence)
        inside_before = point_inside_geofence(previous.latitude, previous.longitude, geofence) if previous else False
        event_type = None
        if inside_now and not inside_before and geofence.alert_on_enter:
            event_type = "ENTER"
        elif inside_before and not inside_now and geofence.alert_on_exit:
            event_type = "EXIT"
        if not event_type:
            continue
        dedupe_key = f"geofence:{geofence.id}:{truck_id}:{event_type}:{event_id}"
        existing = db.scalar(select(GeofenceEvent).where(GeofenceEvent.company_id == company_id, GeofenceEvent.dedupe_key == dedupe_key, GeofenceEvent.deleted_at.is_(None)))
        if existing:
            continue
        event = GeofenceEvent(
            company_id=company_id,
            geofence_id=geofence.id,
            truck_id=truck_id,
            trip_id=trip_id,
            event_type=event_type,
            latitude=latitude,
            longitude=longitude,
            event_at=recorded_at,
            dedupe_key=dedupe_key,
            payload_json=to_json({"geofence_name": geofence.name, "geofence_type": geofence.geofence_type, "event_id": event_id}),
            created_by=created_by,
        )
        db.add(event)
        db.flush()
        geofence_events += 1
        created = _create_alert(
            db,
            company_id=company_id,
            alert_type=f"geofence_{event_type.lower()}",
            severity="critical" if geofence.geofence_type == "RESTRICTED" else "warning",
            title=f"Geofence {event_type.lower()}: {geofence.name}",
            message=f"Camião registou {event_type.lower()} em {geofence.name}.",
            dedupe_key=dedupe_key,
            truck_id=truck_id,
            trip_id=trip_id,
            payload={"latitude": latitude, "longitude": longitude, "geofence_id": geofence.id, "event_type": event_type},
            created_by=created_by,
            geofence_event_id=event.id,
        )
        if created:
            alerts += 1
    return geofence_events, alerts


def record_gps_ingest(
    db: Session,
    *,
    company_id: str,
    created_by: str | None,
    provider: str,
    event_id: str,
    truck_id: str | None,
    trip_id: str | None,
    latitude: float | None,
    longitude: float | None,
    speed_kmh: float | None,
    payload: dict[str, Any],
    heading: float | None = None,
    fuel_level_percent: float | None = None,
    vehicle_state: str = "moving",
    recorded_at: datetime | None = None,
) -> dict[str, Any]:
    existing = _existing_event(db, company_id, provider, event_id)
    if existing:
        existing_payload = _loads(existing.payload_json, {})
        return {
            "event_id": event_id,
            "integration_event_id": existing.id,
            "gps_position_id": existing_payload.get("gps_position_id"),
            "status": existing.status,
            "alerts_created": 0,
            "geofence_events_created": 0,
        }

    if truck_id:
        truck = db.scalar(select(Truck).where(Truck.id == truck_id, Truck.company_id == company_id, Truck.deleted_at.is_(None)))
        if not truck:
            raise HTTPException(status_code=404, detail="Camião não encontrado para o dispositivo GPS")
    if trip_id:
        trip = db.scalar(select(Trip).where(Trip.id == trip_id, Trip.company_id == company_id, Trip.deleted_at.is_(None)))
        if not trip:
            raise HTTPException(status_code=404, detail="Viagem não encontrada para o dispositivo GPS")
        if truck_id and trip.truck_id != truck_id:
            raise HTTPException(status_code=422, detail="A viagem informada não pertence ao camião do dispositivo GPS")

    timestamp = recorded_at or now_utc()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    gps_position: GPSPosition | None = None
    if truck_id and latitude is not None and longitude is not None:
        gps_position = GPSPosition(
            company_id=company_id,
            truck_id=truck_id,
            trip_id=trip_id,
            latitude=latitude,
            longitude=longitude,
            speed_kmh=speed_kmh or 0,
            heading=heading,
            vehicle_state=vehicle_state,
            fuel_level_percent=fuel_level_percent,
            recorded_at=timestamp,
            created_by=created_by,
        )
        db.add(gps_position)
        db.flush()

    event_payload = {**payload, "event_id": event_id, "speed_kmh": speed_kmh, "gps_position_id": gps_position.id if gps_position else None}
    event = GPSIntegrationEvent(
        company_id=company_id,
        truck_id=truck_id,
        trip_id=trip_id,
        provider=provider,
        latitude=latitude,
        longitude=longitude,
        payload_json=json.dumps(event_payload, ensure_ascii=False),
        status="processed",
        processed_at=timestamp,
        created_by=created_by,
    )
    db.add(event)
    db.flush()

    alerts_created = 0
    threshold, rule = _speed_threshold(db, company_id)
    if speed_kmh is not None and speed_kmh > threshold:
        created = _create_alert(
            db,
            company_id=company_id,
            alert_type="speeding",
            severity=rule.severity if rule else "warning",
            title="Alerta de excesso de velocidade",
            message=f"Velocidade registada: {speed_kmh:.0f} km/h",
            dedupe_key=f"speeding:{truck_id or 'unknown'}:{event_id}",
            truck_id=truck_id,
            trip_id=trip_id,
            payload={"speed_kmh": speed_kmh, "threshold": threshold, "provider": provider, "event_id": event_id},
            created_by=created_by,
            rule_id=rule.id if rule else None,
        )
        if created:
            alerts_created += 1

    geofence_events = 0
    if gps_position and latitude is not None and longitude is not None:
        geofence_events, geofence_alerts = evaluate_geofences(
            db,
            company_id=company_id,
            truck_id=truck_id,
            trip_id=trip_id,
            latitude=latitude,
            longitude=longitude,
            recorded_at=timestamp,
            event_id=event_id,
            created_by=created_by,
        )
        alerts_created += geofence_alerts

    return {
        "event_id": event_id,
        "integration_event_id": event.id,
        "gps_position_id": gps_position.id if gps_position else None,
        "status": event.status,
        "alerts_created": alerts_created,
        "geofence_events_created": geofence_events,
    }


def replay_payload(positions: list[GPSPosition]) -> dict[str, Any]:
    items = [
        {
            "id": item.id,
            "truck_id": item.truck_id,
            "trip_id": item.trip_id,
            "latitude": item.latitude,
            "longitude": item.longitude,
            "speed_kmh": item.speed_kmh,
            "heading": item.heading,
            "vehicle_state": item.vehicle_state,
            "fuel_level_percent": item.fuel_level_percent,
            "recorded_at": item.recorded_at,
        }
        for item in positions
    ]
    if not items:
        return {"mode": "replay", "count": 0, "bounds": None, "positions": [], "stops": []}
    lats = [item["latitude"] for item in items]
    lons = [item["longitude"] for item in items]
    return {
        "mode": "replay",
        "count": len(items),
        "bounds": [min(lons), min(lats), max(lons), max(lats)],
        "positions": items,
        "stops": [item for item in items if item["vehicle_state"] == "stopped" or item["speed_kmh"] <= 1],
    }


def geojson_payload(positions: list[GPSPosition]) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    line = [[item.longitude, item.latitude] for item in positions]
    if len(line) >= 2:
        features.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": line}, "properties": {"kind": "gps_route", "points": len(line)}})
    for item in positions:
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [item.longitude, item.latitude]},
                "properties": {
                    "id": item.id,
                    "truck_id": item.truck_id,
                    "trip_id": item.trip_id,
                    "speed_kmh": item.speed_kmh,
                    "recorded_at": item.recorded_at.isoformat(),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}
