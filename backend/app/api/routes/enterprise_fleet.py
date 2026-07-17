from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.schemas.enterprise import FleetCommandCreate
from app.services.fleet_service import command_center, create_command, fleet_compliance_center

router = APIRouter(prefix="/fleet")


@router.get("/command-center")
def fleet_command_center(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    return command_center(db, user)


@router.get("/compliance")
def fleet_compliance(user: User = Depends(require_permission("fleet.view")), db: Session = Depends(get_db)):
    return fleet_compliance_center(db, user)


@router.post("/commands", status_code=201)
def create_fleet_command(payload: FleetCommandCreate, user: User = Depends(require_permission("fleet.manage")), db: Session = Depends(get_db)):
    record = create_command(db, user, payload)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "status": record.status, "command_type": record.command_type}
