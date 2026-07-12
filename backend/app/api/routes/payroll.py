from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.schemas.enterprise import PayrollRunCreate
from app.services.payroll_service import create_payroll_run

router = APIRouter(prefix="/hr/payroll-runs")


@router.post("", status_code=201)
def post_payroll_run(payload: PayrollRunCreate, user: User = Depends(require_permission("hr.manage")), db: Session = Depends(get_db)):
    try:
        run = create_payroll_run(db, user, payload.period)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(run)
    return {"id": run.id, "period": run.period, "status": run.status, "gross_total": float(run.gross_total), "net_total": float(run.net_total), "employees": len(run.items)}
