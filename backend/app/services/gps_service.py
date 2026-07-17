from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FleetCommand, GPSIntegrationEvent, User
from app.services.enterprise_utils import now_utc, to_json
from app.services.gps_tracking_service import record_gps_ingest
from app.services.notification_service import create_notification


def ingest_gps_event(db: Session, user: User, payload) -> GPSIntegrationEvent:
    event_id = payload.payload.get("event_id") if isinstance(payload.payload, dict) else None
    if payload.truck_id and payload.latitude is not None and payload.longitude is not None:
        result = record_gps_ingest(
            db,
            company_id=user.company_id,
            created_by=user.id,
            provider=payload.provider,
            event_id=event_id or f"enterprise-{payload.provider}-{payload.truck_id}-{now_utc().timestamp()}",
            truck_id=payload.truck_id,
            trip_id=payload.trip_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed_kmh=payload.speed_kmh,
            payload=payload.payload,
        )
        event = db.get(GPSIntegrationEvent, result["integration_event_id"])
        if event:
            return event
    if event_id:
        existing = db.scalar(select(GPSIntegrationEvent).where(
            GPSIntegrationEvent.company_id == user.company_id,
            GPSIntegrationEvent.provider == payload.provider,
            GPSIntegrationEvent.truck_id == payload.truck_id,
            GPSIntegrationEvent.payload_json.contains(str(event_id)),
            GPSIntegrationEvent.deleted_at.is_(None),
        ))
        if existing:
            return existing
    event = GPSIntegrationEvent(
        company_id=user.company_id,
        truck_id=payload.truck_id,
        trip_id=payload.trip_id,
        provider=payload.provider,
        latitude=payload.latitude,
        longitude=payload.longitude,
        payload_json=to_json({**payload.payload, "speed_kmh": payload.speed_kmh}),
        status="processed",
        processed_at=now_utc(),
        created_by=user.id,
    )
    db.add(event)
    if payload.speed_kmh is not None and payload.speed_kmh > 90:
        db.add(FleetCommand(
            company_id=user.company_id,
            truck_id=payload.truck_id,
            trip_id=payload.trip_id,
            command_type="speeding_alert",
            priority="high",
            payload_json=to_json({"speed_kmh": payload.speed_kmh, "source": payload.provider, "event_id": event_id}),
            status="open",
            created_by=user.id,
        ))
        create_notification(db, user.company_id, "Alerta de excesso de velocidade", f"Velocidade registada: {payload.speed_kmh:.0f} km/h", "warning", created_by=user.id, dedupe_key=f"speeding-{event_id or payload.truck_id}")
    return event


def gps_history(db: Session, user: User, limit: int = 100) -> list[GPSIntegrationEvent]:
    return list(db.scalars(select(GPSIntegrationEvent).where(GPSIntegrationEvent.company_id == user.company_id, GPSIntegrationEvent.deleted_at.is_(None)).order_by(GPSIntegrationEvent.created_at.desc()).limit(limit)))
