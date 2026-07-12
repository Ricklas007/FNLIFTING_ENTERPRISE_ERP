from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FleetCommand, GPSIntegrationEvent, Trip, Truck, User
from app.services.enterprise_utils import from_json, to_json
from app.services.notification_service import create_notification


def command_center(db: Session, user: User) -> dict:
    commands = db.scalars(select(FleetCommand).where(FleetCommand.company_id == user.company_id, FleetCommand.deleted_at.is_(None)).order_by(FleetCommand.created_at.desc()).limit(80))
    gps_events = db.scalars(select(GPSIntegrationEvent).where(GPSIntegrationEvent.company_id == user.company_id, GPSIntegrationEvent.deleted_at.is_(None)).order_by(GPSIntegrationEvent.created_at.desc()).limit(20))
    trucks = db.scalars(select(Truck).where(Truck.company_id == user.company_id, Truck.deleted_at.is_(None)).order_by(Truck.plate))
    return {
        "summary": {
            "trucks": db.scalar(select(func.count(Truck.id)).where(Truck.company_id == user.company_id, Truck.deleted_at.is_(None))) or 0,
            "active_trips": db.scalar(select(func.count(Trip.id)).where(Trip.company_id == user.company_id, Trip.status.in_(["planned", "in_progress", "delayed"]), Trip.deleted_at.is_(None))) or 0,
            "open_commands": db.scalar(select(func.count(FleetCommand.id)).where(FleetCommand.company_id == user.company_id, FleetCommand.status == "open", FleetCommand.deleted_at.is_(None))) or 0,
            "gps_events": db.scalar(select(func.count(GPSIntegrationEvent.id)).where(GPSIntegrationEvent.company_id == user.company_id, GPSIntegrationEvent.deleted_at.is_(None))) or 0,
        },
        "trucks": [{"id": row.id, "plate": row.plate, "status": row.status, "driver_id": row.driver_id} for row in trucks],
        "commands": [{
            "id": item.id,
            "command_type": item.command_type,
            "priority": item.priority,
            "status": item.status,
            "payload": from_json(item.payload_json, {}),
            "truck_id": item.truck_id,
            "trip_id": item.trip_id,
            "due_at": item.due_at,
            "created_at": item.created_at,
        } for item in commands],
        "gps_events": [{
            "id": item.id,
            "provider": item.provider,
            "latitude": item.latitude,
            "longitude": item.longitude,
            "payload": from_json(item.payload_json, {}),
            "status": item.status,
            "created_at": item.created_at,
        } for item in gps_events],
    }


def create_command(db: Session, user: User, payload) -> FleetCommand:
    record = FleetCommand(
        company_id=user.company_id,
        truck_id=payload.truck_id,
        trip_id=payload.trip_id,
        command_type=payload.command_type,
        priority=payload.priority,
        payload_json=to_json(payload.payload),
        assigned_to=payload.assigned_to,
        due_at=payload.due_at,
        status="open",
        created_by=user.id,
    )
    db.add(record)
    create_notification(db, user.company_id, "Comando logístico criado", f"{payload.command_type} · prioridade {payload.priority}", "warning" if payload.priority in {"high", "critical"} else "info", created_by=user.id)
    return record
