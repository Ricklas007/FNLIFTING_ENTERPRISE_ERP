from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import User
from app.schemas.enterprise import CustomerMessageCreate
from app.services.customer_service import create_customer_message, list_customer_messages

router = APIRouter(prefix="/customer")


@router.get("/messages")
def customer_messages(user: User = Depends(require_permission("client_portal.view")), db: Session = Depends(get_db)):
    return list_customer_messages(db, user)


@router.post("/messages", status_code=201)
def post_customer_message(payload: CustomerMessageCreate, user: User = Depends(require_permission("client_portal.view")), db: Session = Depends(get_db)):
    record = create_customer_message(db, user, payload)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "status": record.status}
