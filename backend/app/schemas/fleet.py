from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.operations import ClientOut


class DriverCreate(BaseModel):
    employee_id: str | None = None
    driver_code: str = Field(min_length=2, max_length=40)
    full_name: str = Field(min_length=2, max_length=180)
    license_number: str = Field(min_length=3, max_length=60)
    license_category: str = Field(min_length=1, max_length=30)
    license_expires_at: date
    phone: str | None = Field(default=None, max_length=40)
    rating: float = Field(default=5, ge=0, le=5)
    status: str = Field(default="available", pattern="^(available|on_trip|inactive|suspended)$")


class DriverUpdate(BaseModel):
    employee_id: str | None = None
    driver_code: str | None = Field(default=None, min_length=2, max_length=40)
    full_name: str | None = Field(default=None, min_length=2, max_length=180)
    license_number: str | None = Field(default=None, min_length=3, max_length=60)
    license_category: str | None = Field(default=None, min_length=1, max_length=30)
    license_expires_at: date | None = None
    phone: str | None = Field(default=None, max_length=40)
    rating: float | None = Field(default=None, ge=0, le=5)
    status: str | None = Field(default=None, pattern="^(available|on_trip|inactive|suspended)$")


class DriverOut(DriverCreate):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TruckCreate(BaseModel):
    driver_id: str | None = None
    plate: str = Field(min_length=3, max_length=30)
    brand: str = Field(min_length=2, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    manufacture_year: int | None = Field(default=None, ge=1950, le=2100)
    truck_type: str = Field(default="fuel_tanker", max_length=60)
    tank_capacity_liters: float | None = Field(default=None, gt=0)
    chassis_number: str | None = Field(default=None, max_length=100)
    insurance_expires_at: date | None = None
    license_expires_at: date | None = None
    inspection_expires_at: date | None = None
    status: str = Field(default="available", pattern="^(available|in_route|maintenance|out_of_service)$")


class TruckUpdate(BaseModel):
    driver_id: str | None = None
    plate: str | None = Field(default=None, min_length=3, max_length=30)
    brand: str | None = Field(default=None, min_length=2, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    manufacture_year: int | None = Field(default=None, ge=1950, le=2100)
    truck_type: str | None = Field(default=None, max_length=60)
    tank_capacity_liters: float | None = Field(default=None, gt=0)
    chassis_number: str | None = Field(default=None, max_length=100)
    insurance_expires_at: date | None = None
    license_expires_at: date | None = None
    inspection_expires_at: date | None = None
    status: str | None = Field(default=None, pattern="^(available|in_route|maintenance|out_of_service)$")


class TruckOut(TruckCreate):
    id: str
    driver: DriverOut | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TripCreate(BaseModel):
    truck_id: str
    driver_id: str
    client_id: str | None = None
    trip_code: str | None = Field(default=None, max_length=40)
    origin: str = Field(min_length=2, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    province: str = Field(min_length=2, max_length=80)
    city: str | None = Field(default=None, max_length=100)
    fuel_type: str | None = Field(default=None, max_length=60)
    quantity_liters: float | None = Field(default=None, gt=0)
    departure_at: datetime | None = None
    expected_arrival_at: datetime | None = None
    actual_arrival_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=3000)
    status: str = Field(default="planned", pattern="^(planned|in_progress|delivered|delayed|cancelled|incident)$")


class TripUpdate(BaseModel):
    truck_id: str | None = None
    driver_id: str | None = None
    client_id: str | None = None
    origin: str | None = Field(default=None, min_length=2, max_length=120)
    destination: str | None = Field(default=None, min_length=2, max_length=120)
    province: str | None = Field(default=None, min_length=2, max_length=80)
    city: str | None = Field(default=None, max_length=100)
    fuel_type: str | None = Field(default=None, max_length=60)
    quantity_liters: float | None = Field(default=None, gt=0)
    departure_at: datetime | None = None
    expected_arrival_at: datetime | None = None
    actual_arrival_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=3000)
    status: str | None = Field(default=None, pattern="^(planned|in_progress|delivered|delayed|cancelled|incident)$")


class TripOut(BaseModel):
    id: str
    truck_id: str
    driver_id: str
    client_id: str | None
    trip_code: str
    origin: str
    destination: str
    province: str
    city: str | None
    fuel_type: str | None
    quantity_liters: float | None
    departure_at: datetime | None
    expected_arrival_at: datetime | None
    actual_arrival_at: datetime | None
    notes: str | None
    status: str
    truck: TruckOut
    driver: DriverOut
    client: ClientOut | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class GPSPositionCreate(BaseModel):
    truck_id: str
    trip_id: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_kmh: float = Field(default=0, ge=0, le=250)
    heading: float | None = Field(default=None, ge=0, le=360)
    vehicle_state: str = Field(default="moving", pattern="^(moving|stopped|offline|incident)$")
    fuel_level_percent: float | None = Field(default=None, ge=0, le=100)
    recorded_at: datetime | None = None


class GPSPositionOut(BaseModel):
    id: str
    truck_id: str
    trip_id: str | None
    latitude: float
    longitude: float
    speed_kmh: float
    heading: float | None
    vehicle_state: str
    fuel_level_percent: float | None
    recorded_at: datetime
    truck: TruckOut
    model_config = ConfigDict(from_attributes=True)


class FuelRecordOut(BaseModel):
    id: str
    trip_id: str
    driver_id: str
    quantity_liters: float
    amount: Decimal
    location: str
    recorded_at: datetime
    receipt_path: str | None
    model_config = ConfigDict(from_attributes=True)


class FleetIncidentOut(BaseModel):
    id: str
    trip_id: str
    driver_id: str
    incident_type: str
    occurred_at: datetime
    location: str | None
    description: str
    photo_path: str | None
    status: str
    model_config = ConfigDict(from_attributes=True)


class FleetSummary(BaseModel):
    drivers_total: int
    drivers_available: int
    trucks_total: int
    trucks_in_route: int
    trips_active: int
    trips_delayed: int
    open_incidents: int
    gps_online: int
