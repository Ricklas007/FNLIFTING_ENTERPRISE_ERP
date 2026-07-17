from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Driver, FleetCommand, FleetIncident, FuelRecord, GPSIntegrationEvent, GPSPosition, Trip, Truck, User
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


def _expiry_state(value: date | None, *, warning_days: int = 30) -> dict:
    if value is None:
        return {"status": "missing", "valid_until": None, "days_remaining": None}
    today = date.today()
    days = (value - today).days
    if days < 0:
        status = "expired"
    elif days <= warning_days:
        status = "expiring"
    else:
        status = "valid"
    return {"status": status, "valid_until": value, "days_remaining": days}


def fleet_compliance_center(db: Session, user: User) -> dict:
    trucks = list(db.scalars(select(Truck).where(Truck.company_id == user.company_id, Truck.deleted_at.is_(None)).order_by(Truck.plate)))
    truck_ids = [truck.id for truck in trucks]
    trip_rows = list(db.scalars(select(Trip).where(Trip.company_id == user.company_id, Trip.deleted_at.is_(None), Trip.truck_id.in_(truck_ids)).order_by(Trip.created_at.desc()))) if truck_ids else []
    incident_rows = list(db.scalars(select(FleetIncident).where(FleetIncident.company_id == user.company_id, FleetIncident.deleted_at.is_(None), FleetIncident.status != "closed"))) if truck_ids else []
    latest_gps_rows = list(db.scalars(select(GPSPosition).where(GPSPosition.company_id == user.company_id, GPSPosition.deleted_at.is_(None), GPSPosition.truck_id.in_(truck_ids)).order_by(GPSPosition.recorded_at.desc()))) if truck_ids else []
    latest_by_truck: dict[str, GPSPosition] = {}
    for gps in latest_gps_rows:
        latest_by_truck.setdefault(gps.truck_id, gps)
    trips_by_truck: dict[str, list[Trip]] = {}
    for trip in trip_rows:
        trips_by_truck.setdefault(trip.truck_id, []).append(trip)
    incidents_by_trip: dict[str, int] = {}
    for incident in incident_rows:
        incidents_by_trip[incident.trip_id] = incidents_by_trip.get(incident.trip_id, 0) + 1
    fuel_by_trip: dict[str, float] = {}
    if trip_rows:
        fuel_rows = db.execute(
            select(FuelRecord.trip_id, func.coalesce(func.sum(FuelRecord.quantity_liters), 0)).where(
                FuelRecord.company_id == user.company_id,
                FuelRecord.deleted_at.is_(None),
                FuelRecord.trip_id.in_([trip.id for trip in trip_rows]),
            ).group_by(FuelRecord.trip_id)
        ).all()
        fuel_by_trip = {trip_id: float(quantity or 0) for trip_id, quantity in fuel_rows}
    driver_ids = {truck.driver_id for truck in trucks if truck.driver_id}
    drivers = {
        driver.id: driver for driver in db.scalars(select(Driver).where(Driver.id.in_(driver_ids), Driver.company_id == user.company_id, Driver.deleted_at.is_(None))).all()
    } if driver_ids else {}

    rows: list[dict] = []
    expiring = expired = missing = 0
    for truck in trucks:
        driver = drivers.get(truck.driver_id or "")
        documents = [
            {"type": "insurance", "label": "Seguro do veículo", **_expiry_state(truck.insurance_expires_at)},
            {"type": "vehicle_license", "label": "Livrete/licença", **_expiry_state(truck.license_expires_at)},
            {"type": "technical_inspection", "label": "Inspeção técnica", **_expiry_state(truck.inspection_expires_at)},
            {"type": "driver_license", "label": "Carta do motorista", **_expiry_state(driver.license_expires_at if driver else None)},
        ]
        for doc in documents:
            if doc["status"] == "expiring":
                expiring += 1
            elif doc["status"] == "expired":
                expired += 1
            elif doc["status"] == "missing":
                missing += 1
        truck_trips = trips_by_truck.get(truck.id, [])
        active_trip = next((trip for trip in truck_trips if trip.status in {"planned", "in_progress", "delayed"}), None)
        open_incidents = sum(incidents_by_trip.get(trip.id, 0) for trip in truck_trips)
        fuel_liters = sum(fuel_by_trip.get(trip.id, 0) for trip in truck_trips)
        latest_gps = latest_by_truck.get(truck.id)
        is_trailer = any(token in (truck.truck_type or "").lower() for token in ["trailer", "semi", "reboque"])
        rows.append({
            "truck_id": truck.id,
            "plate": truck.plate,
            "truck_type": truck.truck_type,
            "is_tanker": bool(truck.tank_capacity_liters),
            "is_trailer": is_trailer,
            "tank_capacity_liters": truck.tank_capacity_liters,
            "driver": {"id": driver.id, "name": driver.full_name, "license_category": driver.license_category} if driver else None,
            "documents": documents,
            "active_trip": {"id": active_trip.id, "trip_code": active_trip.trip_code, "origin": active_trip.origin, "destination": active_trip.destination, "status": active_trip.status} if active_trip else None,
            "open_incidents": open_incidents,
            "fuel_liters_recorded": round(fuel_liters, 2),
            "latest_gps": {"latitude": latest_gps.latitude, "longitude": latest_gps.longitude, "speed_kmh": latest_gps.speed_kmh, "recorded_at": latest_gps.recorded_at} if latest_gps else None,
            "maintenance": {
                "status": "scheduled" if truck.inspection_expires_at and truck.inspection_expires_at <= date.today() + timedelta(days=30) else "ok",
                "next_due": truck.inspection_expires_at,
            },
        })
    return {
        "summary": {
            "trucks": len(rows),
            "tankers": sum(1 for item in rows if item["is_tanker"]),
            "trailers": sum(1 for item in rows if item["is_trailer"]),
            "documents_expiring": expiring,
            "documents_expired": expired,
            "documents_missing": missing,
            "open_incidents": sum(item["open_incidents"] for item in rows),
        },
        "items": rows,
    }
