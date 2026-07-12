from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.schemas.enterprise import AttendanceCreate, LeaveRequestCreate
from app.services.hr_enterprise_service import create_attendance, create_leave_request, employee_portal

router = APIRouter(prefix="/hr")


@router.get("/employee-portal")
def get_employee_portal(user: User = Depends(require_permission("hr.view")), db: Session = Depends(get_db)):
    return employee_portal(db, user)


@router.post("/attendance", status_code=201)
def post_attendance(payload: AttendanceCreate, user: User = Depends(require_permission("hr.manage")), db: Session = Depends(get_db)):
    try:
        record = create_attendance(db, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(record)
    return {"id": record.id, "status": record.status, "approval_status": record.approval_status}


@router.post("/leave-requests", status_code=201)
def post_leave_request(payload: LeaveRequestCreate, user: User = Depends(require_permission("hr.manage")), db: Session = Depends(get_db)):
    try:
        record = create_leave_request(db, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422 if "data" in str(exc) else 404, detail=str(exc)) from exc
    db.commit()
    db.refresh(record)
    return {"id": record.id, "status": record.status}
