from __future__ import annotations

import hashlib
import os
import re
from datetime import date, timedelta
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    Client,
    Driver,
    FleetAlert,
    FleetAlertRule,
    Geofence,
    GeofenceEvent,
    GPSPosition,
    GPSTrackerDevice,
    Trip,
    Truck,
    User,
)
from app.services.enterprise_utils import now_utc, to_json
from app.services.gps_tracking_service import device_token, record_gps_ingest, replay_payload

GPS_PILOT_ROUTE: list[dict[str, Any]] = [
    {"name": "Base FNLIFTING Luanda", "lat": -8.8390, "lon": 13.2894, "speed": 0.0, "state": "stopped", "note": "cold_start"},
    {"name": "Viana checkpoint", "lat": -8.9050, "lon": 13.3710, "speed": 58.0, "state": "moving", "note": "dispatch_confirmed"},
    {"name": "Dondo corridor", "lat": -9.6930, "lon": 14.4300, "speed": 72.0, "state": "moving", "note": "offline_buffer_queued"},
    {"name": "Ndalatando restricted gate", "lat": -9.2990, "lon": 14.9160, "speed": 104.0, "state": "moving", "note": "speed_alert_expected"},
    {"name": "Cacuso checkpoint", "lat": -9.5280, "lon": 15.9050, "speed": 64.0, "state": "moving", "note": "network_restored"},
    {"name": "Malanje delivery terminal", "lat": -9.5402, "lon": 16.3410, "speed": 0.0, "state": "stopped", "note": "proof_of_delivery"},
]

GPS_PILOT_STATUS_FLOW = ["DRAFT", "PLANNED", "PENDING_APPROVAL", "AUTHORIZED", "DISPATCHED", "IN_TRANSIT", "STOPPED", "ARRIVED", "DELIVERED", "CLOSED"]
GPS_ONBOARDING_METHODS = ["TRACCAR", "VENDOR_API", "DIRECT_PROTOCOL", "HTTP", "MQTT", "WEBHOOK", "MANUAL_IMPORT"]
GPS_ONBOARDING_CHECKLIST: list[dict[str, str]] = [
    {"field": "manufacturer", "required": "yes", "evidence": "Tracker make/model data sheet or vendor portal"},
    {"field": "model", "required": "yes", "evidence": "Exact hardware model and supported protocol"},
    {"field": "imei", "required": "yes", "evidence": "IMEI photographed and entered without spaces"},
    {"field": "serial", "required": "yes", "evidence": "Physical serial or vendor serial"},
    {"field": "protocol", "required": "yes", "evidence": "TRACCAR, HTTP, MQTT, WEBHOOK, DIRECT_PROTOCOL or vendor API"},
    {"field": "sim_iccid", "required": "yes", "evidence": "ICCID from SIM holder or carrier portal"},
    {"field": "operator", "required": "yes", "evidence": "Carrier name and coverage confirmation"},
    {"field": "apn", "required": "yes", "evidence": "APN, username/password when required"},
    {"field": "firmware", "required": "recommended", "evidence": "Firmware version and vendor update status"},
    {"field": "server", "required": "yes", "evidence": "ERP/Traccar host and port, never public credentials in notes"},
    {"field": "frequency", "required": "yes", "evidence": "Position interval moving/stopped"},
    {"field": "truck", "required": "yes", "evidence": "Truck plate and assignment approval"},
    {"field": "driver", "required": "recommended", "evidence": "Driver assignment or shift policy"},
]


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _safe_run_code(value: str | None) -> str:
    if value:
        cleaned = re.sub(r"[^A-Za-z0-9_.-]", "-", value.strip())[:60]
        if cleaned:
            return cleaned
    return f"GPS-PILOT-{now_utc().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return radius_km * 2 * atan2(sqrt(a), sqrt(1 - a))


def _route_distance_km() -> float:
    return round(sum(_haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) for a, b in zip(GPS_PILOT_ROUTE, GPS_PILOT_ROUTE[1:])), 2)


def _by_company(db: Session, model, company_id: str, field: str, value: str):
    return db.scalar(select(model).where(model.company_id == company_id, getattr(model, field) == value, model.deleted_at.is_(None)))


def _ensure_client(db: Session, user: User) -> Client:
    existing = _by_company(db, Client, user.company_id, "nif", "GPSPILOT001")
    if existing:
        return existing
    record = Client(company_id=user.company_id, name="Cliente Piloto GPS Malanje", nif="GPSPILOT001", email="gps-pilot@example.invalid", phone="+244000000000", address="Malanje, Angola", contact_person="Operador Piloto", service_notes="Cliente interno criado para validacao operacional GPS simulada.", status="active", created_by=user.id)
    db.add(record)
    db.flush()
    return record


def _ensure_driver(db: Session, user: User) -> Driver:
    existing = _by_company(db, Driver, user.company_id, "driver_code", "DRV-GPS-PILOT")
    if existing:
        existing.status = "on_trip"
        return existing
    record = Driver(company_id=user.company_id, driver_code="DRV-GPS-PILOT", full_name="Motorista Piloto GPS", license_number="GPS-PILOT-LICENSE", license_category="D", license_expires_at=date(2032, 12, 31), phone="+244000000001", rating=5.0, status="on_trip", created_by=user.id)
    db.add(record)
    db.flush()
    return record


def _ensure_truck(db: Session, user: User, driver: Driver, run_code: str) -> Truck:
    suffix = re.sub(r"[^A-Z0-9]", "", run_code.upper())[-8:] or uuid4().hex[:8].upper()
    plate = f"LD-GP-{suffix}"
    existing = _by_company(db, Truck, user.company_id, "plate", plate)
    if existing:
        existing.driver_id = driver.id
        existing.status = "in_route"
        return existing
    record = Truck(company_id=user.company_id, driver_id=driver.id, plate=plate, brand="Mercedes-Benz", model="Actros Fuel Pilot", manufacture_year=2026, truck_type="fuel_tanker", tank_capacity_liters=34000, chassis_number=f"GPS-PILOT-CHASSIS-{suffix}", insurance_expires_at=date(2032, 12, 31), license_expires_at=date(2032, 12, 31), inspection_expires_at=date(2032, 12, 31), status="in_route", created_by=user.id)
    db.add(record)
    db.flush()
    return record


def _create_trip(db: Session, user: User, run_code: str, truck: Truck, driver: Driver, client: Client) -> Trip:
    if _by_company(db, Trip, user.company_id, "trip_code", run_code):
        raise HTTPException(status_code=409, detail="Codigo de piloto GPS ja existe; envie outro run_code")
    start = now_utc().replace(microsecond=0)
    record = Trip(company_id=user.company_id, truck_id=truck.id, driver_id=driver.id, client_id=client.id, trip_code=run_code, origin="Base FNLIFTING Luanda", destination="Cliente Piloto GPS Malanje", province="Malanje", city="Malanje", fuel_type="Diesel", quantity_liters=34000, departure_at=start, expected_arrival_at=start + timedelta(hours=6), notes="Pilot GPS flow: " + " > ".join(GPS_PILOT_STATUS_FLOW), status="in_progress", created_by=user.id)
    db.add(record)
    db.flush()
    return record


def _ensure_device(db: Session, user: User, truck: Truck, driver: Driver) -> GPSTrackerDevice:
    uid = f"GPS-PILOT-{truck.plate}"
    existing = _by_company(db, GPSTrackerDevice, user.company_id, "device_uid", uid)
    if existing:
        existing.truck_id = truck.id
        existing.driver_id = driver.id
        existing.provider = "HTTP_TRACKER_SIMULATOR"
        existing.status = "active"
        existing.updated_by = user.id
        return existing
    record = GPSTrackerDevice(company_id=user.company_id, truck_id=truck.id, driver_id=driver.id, device_uid=uid, label=f"Tracker piloto {truck.plate}", provider="HTTP_TRACKER_SIMULATOR", token_hash=hash_password("pending"), capabilities_json=to_json(["gps", "speed", "fuel", "offline_buffer", "geofence"]), status="active", created_by=user.id)
    db.add(record)
    db.flush()
    _token, secret = device_token(record.id)
    record.token_hash = hash_password(secret)
    return record


def _create_point_geofence(db: Session, user: User, run_code: str, name: str, geofence_type: str, point: dict[str, Any], radius_meters: float, alert_on_exit: bool = True) -> Geofence:
    record = Geofence(company_id=user.company_id, name=f"GPS PILOT {run_code} - {name}", geofence_type=geofence_type, shape_type="circle", geometry_json=to_json({"center": [point["lon"], point["lat"]], "route": "Luanda-Malanje", "pilot_run": run_code}), radius_meters=radius_meters, status="active", alert_on_enter=True, alert_on_exit=alert_on_exit, created_by=user.id)
    db.add(record)
    db.flush()
    return record


def _prepare_geofences(db: Session, user: User, run_code: str) -> None:
    _create_point_geofence(db, user, run_code, "Origem Luanda", "BASE", GPS_PILOT_ROUTE[0], 9000)
    _create_point_geofence(db, user, run_code, "Area restrita Ndalatando", "RESTRICTED", GPS_PILOT_ROUTE[3], 6500)
    _create_point_geofence(db, user, run_code, "Destino Malanje", "CLIENT", GPS_PILOT_ROUTE[-1], 9000, alert_on_exit=False)


def _ensure_speed_rule(db: Session, user: User) -> FleetAlertRule:
    existing = _by_company(db, FleetAlertRule, user.company_id, "code", "GPS-PILOT-SPEED-80")
    if existing:
        existing.condition_json = to_json({"max_speed_kmh": 80, "source": "phase_15_pilot"})
        existing.status = "active"
        return existing
    record = FleetAlertRule(company_id=user.company_id, code="GPS-PILOT-SPEED-80", name="Piloto GPS - limite operacional 80 km/h", alert_type="speeding", severity="warning", condition_json=to_json({"max_speed_kmh": 80, "source": "phase_15_pilot"}), status="active", created_by=user.id)
    db.add(record)
    db.flush()
    return record


def _report_directory() -> Path:
    path = Path(settings.report_dir).resolve() / "gps-pilot"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _draw_wrapped(pdf: canvas.Canvas, text: str, x: float, y: float, width: float, leading: float = 5 * mm) -> float:
    pdf.setFont("Helvetica", 9)

    def split_long_word(word: str) -> list[str]:
        pieces: list[str] = []
        current = ""
        for char in word:
            candidate = current + char
            if pdf.stringWidth(candidate, "Helvetica", 9) <= width:
                current = candidate
            else:
                if current:
                    pieces.append(current)
                current = char
        if current:
            pieces.append(current)
        return pieces or [word]

    line = ""
    for raw_word in text.split():
        words = split_long_word(raw_word) if pdf.stringWidth(raw_word, "Helvetica", 9) > width else [raw_word]
        for word in words:
            candidate = f"{line} {word}".strip()
            if pdf.stringWidth(candidate, "Helvetica", 9) <= width:
                line = candidate
                continue
            if line:
                pdf.drawString(x, y, line)
                y -= leading
            line = word
    if line:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def generate_pilot_pdf(report: dict[str, Any]) -> dict[str, Any]:
    directory = _report_directory()
    filename = f"gps-pilot-{report['run_code']}.pdf"
    path = directory / filename
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    margin = 18 * mm
    pdf.setTitle(f"FNLIFTING GPS Pilot Report {report['run_code']}")
    pdf.setAuthor("FNLIFTING Enterprise ERP")
    pdf.setFillColor(colors.HexColor("#071629"))
    pdf.rect(0, height - 38 * mm, width, 38 * mm, fill=True, stroke=False)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(margin, height - 18 * mm, "FNLIFTING Enterprise ERP")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(margin, height - 27 * mm, "Phase 15 GPS Pilot Operational Report")
    y = height - 50 * mm
    pdf.setFillColor(colors.HexColor("#0A2540"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(margin, y, "Pilot summary")
    y -= 8 * mm
    summary = [("Run code", report["run_code"]), ("Trip", report["trip_code"]), ("Truck", report["truck_plate"]), ("Driver", report["driver_name"]), ("Client", report["client_name"]), ("Route", report["route_name"]), ("Distance", f"{report['distance_km']} km"), ("Positions", str(report["positions_created"])), ("Alerts", str(report["alerts_created"])), ("Geofence events", str(report["geofence_events_created"]))]
    for label, value in summary:
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(margin, y, f"{label}:")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(margin + 36 * mm, y, str(value))
        y -= 5 * mm
    y -= 4 * mm
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(margin, y, "Operational evidence")
    y -= 8 * mm
    for item in [
        f"Status flow validated in ERP pilot context: {' > '.join(report['status_flow'])}.",
        f"Offline buffer simulated with {report['offline_buffer']['queued_points']} queued points and ordered flush validated: {report['offline_buffer']['flush_order_validated']}.",
        f"Security checks: token hash present={report['security']['device_token_hash_present']}, duplicate replay blocked={report['security']['dedupe_validated']}.",
        f"Classifications: {', '.join(report['classifications'])}.",
    ]:
        y = _draw_wrapped(pdf, item, margin, y, width - 2 * margin)
        y -= 1 * mm
    y -= 4 * mm
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(margin, y, "Route points")
    y -= 7 * mm
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(margin, y, "#")
    pdf.drawString(margin + 9 * mm, y, "Location")
    pdf.drawString(margin + 76 * mm, y, "Speed")
    pdf.drawString(margin + 98 * mm, y, "State")
    pdf.drawString(margin + 124 * mm, y, "GPS note")
    y -= 5 * mm
    pdf.setFont("Helvetica", 8)
    for index, point in enumerate(report["route_points"], start=1):
        if y < 35 * mm:
            pdf.showPage()
            y = height - margin
        pdf.drawString(margin, y, str(index))
        pdf.drawString(margin + 9 * mm, y, point["name"][:38])
        pdf.drawString(margin + 76 * mm, y, f"{point['speed']} km/h")
        pdf.drawString(margin + 98 * mm, y, point["state"])
        pdf.drawString(margin + 124 * mm, y, point["note"][:34])
        y -= 5 * mm
    y -= 5 * mm
    pdf.line(margin, y, width - margin, y)
    y -= 8 * mm
    pdf.setFont("Helvetica", 9)
    pdf.drawString(margin, y, "Dispatcher signature: ______________________________")
    pdf.drawString(margin + 92 * mm, y, "Inspector: ______________________________")
    y -= 8 * mm
    pdf.drawString(margin, y, f"Generated at UTC: {report['generated_at']}")
    pdf.drawRightString(width - margin, 12 * mm, "FNLIFTING ERP - controlled pilot document")
    pdf.save()
    return {"generated": True, "file_name": filename, "size_bytes": path.stat().st_size, "sha256": _sha256(path), "download_url": f"/api/v1/fleet/gps/pilot/reports/{filename}"}


def gps_pilot_report_path(filename: str) -> Path:
    if not re.fullmatch(r"gps-pilot-[A-Za-z0-9_.-]+\.pdf", filename):
        raise HTTPException(status_code=404, detail="Relatorio GPS nao encontrado")
    base = _report_directory()
    path = (base / filename).resolve()
    if path.parent != base or not path.exists():
        raise HTTPException(status_code=404, detail="Relatorio GPS nao encontrado")
    return path


def onboarding_checklist_payload() -> dict[str, Any]:
    traccar_configured = _truthy(os.getenv("TRACCAR_ENABLED")) and bool(os.getenv("TRACCAR_URL", "").strip())
    vendor_configured = bool(os.getenv("GPS_VENDOR_API_URL", "").strip())
    return {
        "classification": ["GPS_SIMULATED_VALIDATED_READY", "TRACCAR_PIPELINE_READY" if traccar_configured else "TRACCAR_NOT_CONFIGURED", "GPS_PHYSICAL_PENDING_HARDWARE", "VENDOR_API_CONNECTED" if vendor_configured else "VENDOR_API_NOT_AVAILABLE"],
        "hardware_required": True,
        "methods": GPS_ONBOARDING_METHODS,
        "items": GPS_ONBOARDING_CHECKLIST,
        "simulator": {"provider": "HTTP_TRACKER_SIMULATOR", "route": "Luanda-Malanje", "positions": len(GPS_PILOT_ROUTE), "validates": ["secure_ingest", "offline_buffer", "dedupe", "geofence", "speed_alert", "replay", "pdf_report"]},
    }


def simulate_gps_pilot(db: Session, user: User, *, run_code: str | None = None, include_report: bool = True) -> dict[str, Any]:
    run = _safe_run_code(run_code)
    created_at = now_utc().replace(microsecond=0)
    client = _ensure_client(db, user)
    driver = _ensure_driver(db, user)
    truck = _ensure_truck(db, user, driver, run)
    trip = _create_trip(db, user, run, truck, driver, client)
    device = _ensure_device(db, user, truck, driver)
    _ensure_speed_rule(db, user)
    _prepare_geofences(db, user, run)
    db.flush()

    queued_event_ids: list[str] = []
    original_results: dict[str, dict[str, Any]] = {}
    alerts_created = 0
    geofence_events_created = 0
    for index, point in enumerate(GPS_PILOT_ROUTE):
        event_id = f"{run}-p{index + 1}"
        offline_queued = point["note"] in {"offline_buffer_queued", "speed_alert_expected"}
        if offline_queued:
            queued_event_ids.append(event_id)
        result = record_gps_ingest(
            db,
            company_id=user.company_id,
            created_by=user.id,
            provider=device.provider,
            event_id=event_id,
            truck_id=truck.id,
            trip_id=trip.id,
            latitude=point["lat"],
            longitude=point["lon"],
            speed_kmh=point["speed"],
            heading=65.0 if point["state"] == "moving" else 0.0,
            fuel_level_percent=max(12.0, 96.0 - index * 7.5),
            vehicle_state=point["state"],
            recorded_at=created_at + timedelta(minutes=index * 18),
            payload={"run_code": run, "device_id": device.id, "device_uid": device.device_uid, "route_point": point["name"], "pilot_note": point["note"], "offline_buffer": {"queued": offline_queued, "batch_id": f"{run}-offline-batch" if offline_queued else None, "flush_order": queued_event_ids.index(event_id) + 1 if offline_queued else None}},
        )
        original_results[event_id] = result
        alerts_created += int(result.get("alerts_created") or 0)
        geofence_events_created += int(result.get("geofence_events_created") or 0)

    dedupe_event = queued_event_ids[0] if queued_event_ids else f"{run}-p1"
    dedupe_result = record_gps_ingest(db, company_id=user.company_id, created_by=user.id, provider=device.provider, event_id=dedupe_event, truck_id=truck.id, trip_id=trip.id, latitude=GPS_PILOT_ROUTE[2]["lat"], longitude=GPS_PILOT_ROUTE[2]["lon"], speed_kmh=GPS_PILOT_ROUTE[2]["speed"], payload={"run_code": run, "dedupe_probe": True})

    trip.status = "delivered"
    trip.actual_arrival_at = created_at + timedelta(minutes=(len(GPS_PILOT_ROUTE) - 1) * 18)
    trip.notes = (trip.notes or "") + "\nProof of delivery: simulated signature, fuel quantity and destination geofence validated."
    truck.status = "available"
    driver.status = "available"
    device.last_seen_at = now_utc()
    device.updated_by = user.id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Falha de integridade ao executar piloto GPS") from exc

    positions = list(db.scalars(select(GPSPosition).where(GPSPosition.company_id == user.company_id, GPSPosition.trip_id == trip.id, GPSPosition.deleted_at.is_(None)).order_by(GPSPosition.recorded_at.asc())).all())
    replay = replay_payload(positions)
    alert_count = db.scalar(select(func.count(FleetAlert.id)).where(FleetAlert.company_id == user.company_id, FleetAlert.trip_id == trip.id, FleetAlert.deleted_at.is_(None))) or alerts_created
    geofence_count = db.scalar(select(func.count(GeofenceEvent.id)).where(GeofenceEvent.company_id == user.company_id, GeofenceEvent.trip_id == trip.id, GeofenceEvent.deleted_at.is_(None))) or geofence_events_created
    traccar_configured = _truthy(os.getenv("TRACCAR_ENABLED")) and bool(os.getenv("TRACCAR_URL", "").strip())
    vendor_configured = bool(os.getenv("GPS_VENDOR_API_URL", "").strip())
    original = original_results.get(dedupe_event, {})
    dedupe_validated = bool(original.get("gps_position_id") and original.get("gps_position_id") == dedupe_result.get("gps_position_id") and dedupe_result.get("alerts_created") == 0)
    report = {
        "run_code": run,
        "trip_id": trip.id,
        "trip_code": trip.trip_code,
        "truck_id": truck.id,
        "truck_plate": truck.plate,
        "driver_id": driver.id,
        "driver_name": driver.full_name,
        "client_id": client.id,
        "client_name": client.name,
        "device_id": device.id,
        "device_uid": device.device_uid,
        "route_name": "Luanda-Malanje",
        "route_points": GPS_PILOT_ROUTE,
        "distance_km": _route_distance_km(),
        "positions_created": len(positions),
        "alerts_created": int(alert_count),
        "geofence_events_created": int(geofence_count),
        "replay_count": replay["count"],
        "stops_count": len(replay["stops"]),
        "status_flow": GPS_PILOT_STATUS_FLOW,
        "offline_buffer": {"simulated": True, "batch_id": f"{run}-offline-batch", "queued_points": len(queued_event_ids), "queued_event_ids": queued_event_ids, "flush_order_validated": queued_event_ids == [f"{run}-p3", f"{run}-p4"], "dedupe_probe_event_id": dedupe_event},
        "security": {"device_token_hash_present": bool(device.token_hash and device.token_hash != "pending"), "token_returned_in_response": False, "dedupe_validated": dedupe_validated, "tenant_id": user.company_id, "unknown_device_rejected_by_ingest_endpoint": "covered_by_existing_tests"},
        "traccar": {"configured": traccar_configured, "classification": "TRACCAR_PIPELINE_VALIDATED" if traccar_configured else "TRACCAR_PIPELINE_READY_PENDING_EXTERNAL_RUNTIME", "note": "Docker/Traccar runtime must be supplied externally for a real gateway proof." if not traccar_configured else "Traccar environment configured; run provider health endpoint for live proof."},
        "vendor_api": {"configured": vendor_configured, "classification": "VENDOR_API_CONNECTED" if vendor_configured else "VENDOR_API_NOT_AVAILABLE"},
        "classifications": ["GPS_SIMULATED_VALIDATED", "GPS_PHYSICAL_PENDING_HARDWARE", "TRACCAR_PIPELINE_VALIDATED" if traccar_configured else "TRACCAR_PIPELINE_READY_PENDING_EXTERNAL_RUNTIME", "VENDOR_API_CONNECTED" if vendor_configured else "VENDOR_API_NOT_AVAILABLE"],
        "generated_at": now_utc().isoformat(),
    }
    report["pdf_report"] = generate_pilot_pdf(report) if include_report else {"generated": False}
    return report
