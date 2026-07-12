from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import Client, Driver, FleetIncident, FuelRecord, GPSPosition, Trip, Truck, User
from app.schemas.auth import MessageResponse
from app.schemas.fleet import (
    DriverCreate, DriverOut, DriverUpdate, FleetIncidentOut, FleetSummary, FuelRecordOut,
    GPSPositionCreate, GPSPositionOut, TripCreate, TripOut, TripUpdate, TruckCreate,
    TruckOut, TruckUpdate,
)


router = APIRouter(prefix="/fleet", tags=["Frota, Viagens e GPS"])


def commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


def driver_query():
    return select(Driver)


def truck_query():
    return select(Truck).options(selectinload(Truck.driver))


def trip_query():
    return select(Trip).options(
        selectinload(Trip.driver),
        selectinload(Trip.truck).selectinload(Truck.driver),
        selectinload(Trip.client),
    )


def get_driver(db: Session, record_id: str, company_id: str) -> Driver:
    record = db.scalar(driver_query().where(Driver.id == record_id, Driver.company_id == company_id, Driver.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Motorista não encontrado")
    return record


def get_truck(db: Session, record_id: str, company_id: str) -> Truck:
    record = db.scalar(truck_query().where(Truck.id == record_id, Truck.company_id == company_id, Truck.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Camião não encontrado")
    return record


def get_trip(db: Session, record_id: str, company_id: str) -> Trip:
    record = db.scalar(trip_query().where(Trip.id == record_id, Trip.company_id == company_id, Trip.deleted_at.is_(None)))
    if not record:
        raise HTTPException(status_code=404, detail="Viagem não encontrada")
    return record


@router.get("/summary", response_model=FleetSummary)
def fleet_summary(
    user: User = Depends(require_permission("fleet.view")),
    db: Session = Depends(get_db),
):
    company_id = user.company_id
    latest_trucks = db.scalars(select(GPSPosition.truck_id).where(
        GPSPosition.company_id == company_id,
        GPSPosition.deleted_at.is_(None),
    ).distinct()).all()
    return FleetSummary(
        drivers_total=db.scalar(select(func.count(Driver.id)).where(Driver.company_id == company_id, Driver.deleted_at.is_(None))) or 0,
        drivers_available=db.scalar(select(func.count(Driver.id)).where(Driver.company_id == company_id, Driver.status == "available", Driver.deleted_at.is_(None))) or 0,
        trucks_total=db.scalar(select(func.count(Truck.id)).where(Truck.company_id == company_id, Truck.deleted_at.is_(None))) or 0,
        trucks_in_route=db.scalar(select(func.count(Truck.id)).where(Truck.company_id == company_id, Truck.status == "in_route", Truck.deleted_at.is_(None))) or 0,
        trips_active=db.scalar(select(func.count(Trip.id)).where(Trip.company_id == company_id, Trip.status == "in_progress", Trip.deleted_at.is_(None))) or 0,
        trips_delayed=db.scalar(select(func.count(Trip.id)).where(Trip.company_id == company_id, Trip.status == "delayed", Trip.deleted_at.is_(None))) or 0,
        open_incidents=db.scalar(select(func.count(FleetIncident.id)).where(FleetIncident.company_id == company_id, FleetIncident.status != "closed", FleetIncident.deleted_at.is_(None))) or 0,
        gps_online=len(latest_trucks),
    )


@router.get("/drivers", response_model=list[DriverOut])
def list_drivers(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    return list(db.scalars(driver_query().where(
        Driver.company_id == user.company_id, Driver.deleted_at.is_(None)
    ).order_by(Driver.full_name)).all())


@router.post("/drivers", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(payload: DriverCreate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = Driver(company_id=user.company_id, created_by=user.id, **payload.model_dump())
    db.add(record)
    commit_or_conflict(db, "Código, carta de condução ou trabalhador já associado")
    db.refresh(record)
    return record


@router.patch("/drivers/{driver_id}", response_model=DriverOut)
def update_driver(driver_id: str, payload: DriverUpdate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = get_driver(db, driver_id, user.company_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_by = user.id
    commit_or_conflict(db, "Código ou carta de condução já utilizado")
    return record


@router.delete("/drivers/{driver_id}", response_model=MessageResponse)
def delete_driver(driver_id: str, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = get_driver(db, driver_id, user.company_id)
    linked = db.scalar(select(func.count(Trip.id)).where(Trip.driver_id == record.id, Trip.deleted_at.is_(None))) or 0
    if linked:
        raise HTTPException(status_code=409, detail="O motorista possui histórico de viagens e não pode ser eliminado")
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = user.id
    db.commit()
    return MessageResponse(message="Motorista arquivado")


@router.get("/trucks", response_model=list[TruckOut])
def list_trucks(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    return list(db.scalars(truck_query().where(
        Truck.company_id == user.company_id, Truck.deleted_at.is_(None)
    ).order_by(Truck.plate)).all())


@router.post("/trucks", response_model=TruckOut, status_code=status.HTTP_201_CREATED)
def create_truck(payload: TruckCreate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    if payload.driver_id:
        get_driver(db, payload.driver_id, user.company_id)
    record = Truck(company_id=user.company_id, created_by=user.id, **payload.model_dump())
    db.add(record)
    commit_or_conflict(db, "Matrícula ou chassis já utilizado")
    return get_truck(db, record.id, user.company_id)


@router.patch("/trucks/{truck_id}", response_model=TruckOut)
def update_truck(truck_id: str, payload: TruckUpdate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = get_truck(db, truck_id, user.company_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("driver_id"):
        get_driver(db, changes["driver_id"], user.company_id)
    for field, value in changes.items():
        setattr(record, field, value)
    record.updated_by = user.id
    commit_or_conflict(db, "Matrícula ou chassis já utilizado")
    return get_truck(db, record.id, user.company_id)


@router.delete("/trucks/{truck_id}", response_model=MessageResponse)
def delete_truck(truck_id: str, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = get_truck(db, truck_id, user.company_id)
    linked = db.scalar(select(func.count(Trip.id)).where(Trip.truck_id == record.id, Trip.deleted_at.is_(None))) or 0
    if linked:
        raise HTTPException(status_code=409, detail="O camião possui histórico de viagens e não pode ser eliminado")
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = user.id
    db.commit()
    return MessageResponse(message="Camião arquivado")


@router.get("/trips", response_model=list[TripOut])
def list_trips(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    return list(db.scalars(trip_query().where(
        Trip.company_id == user.company_id, Trip.deleted_at.is_(None)
    ).order_by(Trip.created_at.desc())).unique().all())


@router.post("/trips", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripCreate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    truck = get_truck(db, payload.truck_id, user.company_id)
    driver = get_driver(db, payload.driver_id, user.company_id)
    if payload.client_id:
        client = db.scalar(select(Client).where(Client.id == payload.client_id, Client.company_id == user.company_id, Client.deleted_at.is_(None)))
        if not client:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
    count = db.scalar(select(func.count(Trip.id)).where(Trip.company_id == user.company_id)) or 0
    values = payload.model_dump(exclude={"trip_code"})
    record = Trip(
        company_id=user.company_id,
        trip_code=payload.trip_code or f"TRP-{datetime.now().year}-{count + 1:03d}",
        created_by=user.id,
        **values,
    )
    if record.status == "in_progress":
        truck.status = "in_route"
        driver.status = "on_trip"
    db.add(record)
    commit_or_conflict(db, "Código de viagem já utilizado")
    return get_trip(db, record.id, user.company_id)


@router.patch("/trips/{trip_id}", response_model=TripOut)
def update_trip(trip_id: str, payload: TripUpdate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = get_trip(db, trip_id, user.company_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("truck_id"):
        get_truck(db, changes["truck_id"], user.company_id)
    if changes.get("driver_id"):
        get_driver(db, changes["driver_id"], user.company_id)
    for field, value in changes.items():
        setattr(record, field, value)
    if record.status == "in_progress":
        record.truck.status = "in_route"
        record.driver.status = "on_trip"
    elif record.status in {"delivered", "cancelled"}:
        record.truck.status = "available"
        record.driver.status = "available"
        if record.status == "delivered" and not record.actual_arrival_at:
            record.actual_arrival_at = datetime.now(timezone.utc)
    record.updated_by = user.id
    db.commit()
    return get_trip(db, record.id, user.company_id)


@router.get("/gps/live", response_model=list[GPSPositionOut])
def live_positions(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    records = db.scalars(select(GPSPosition).options(
        selectinload(GPSPosition.truck).selectinload(Truck.driver)
    ).where(
        GPSPosition.company_id == user.company_id,
        GPSPosition.deleted_at.is_(None),
    ).order_by(GPSPosition.recorded_at.desc())).unique().all()
    latest: dict[str, GPSPosition] = {}
    for record in records:
        latest.setdefault(record.truck_id, record)
    return list(latest.values())


@router.get("/gps/trips/{trip_id}", response_model=list[GPSPositionOut])
def trip_positions(trip_id: str, user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    get_trip(db, trip_id, user.company_id)
    return list(db.scalars(select(GPSPosition).options(
        selectinload(GPSPosition.truck).selectinload(Truck.driver)
    ).where(GPSPosition.trip_id == trip_id, GPSPosition.deleted_at.is_(None)).order_by(GPSPosition.recorded_at)).unique().all())


@router.post("/gps/positions", response_model=GPSPositionOut, status_code=status.HTTP_201_CREATED)
def create_position(payload: GPSPositionCreate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    truck = get_truck(db, payload.truck_id, user.company_id)
    if payload.trip_id:
        trip = get_trip(db, payload.trip_id, user.company_id)
        if trip.truck_id != truck.id:
            raise HTTPException(status_code=422, detail="A viagem não pertence ao camião informado")
    values = payload.model_dump(exclude={"recorded_at"})
    record = GPSPosition(
        company_id=user.company_id,
        recorded_at=payload.recorded_at or datetime.now(timezone.utc),
        created_by=user.id,
        **values,
    )
    db.add(record)
    db.commit()
    return db.scalar(select(GPSPosition).options(
        selectinload(GPSPosition.truck).selectinload(Truck.driver)
    ).where(GPSPosition.id == record.id))


@router.get("/fuel-records", response_model=list[FuelRecordOut])
def list_fuel_records(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(FuelRecord).where(
        FuelRecord.company_id == user.company_id, FuelRecord.deleted_at.is_(None)
    ).order_by(FuelRecord.recorded_at.desc())).all())


@router.get("/incidents", response_model=list[FleetIncidentOut])
def list_incidents(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(FleetIncident).where(
        FleetIncident.company_id == user.company_id, FleetIncident.deleted_at.is_(None)
    ).order_by(FleetIncident.occurred_at.desc())).all())
