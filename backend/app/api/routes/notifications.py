from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.database.session import get_db
from app.models import User
from app.services.notification_service import create_notification, list_notifications, mark_read

router = APIRouter(prefix="/notifications")


@router.get("")
def notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_notifications(db, user)


@router.post("/generate-demo")
def generate_demo_notifications(user: User = Depends(require_permission("dashboard.view")), db: Session = Depends(get_db)):
    create_notification(db, user.company_id, "Certificados próximos do vencimento", "O motor de regras encontrou certificados que devem ser revistos.", "warning", created_by=user.id, dedupe_key="cert-expiring-demo")
    create_notification(db, user.company_id, "Backup e sincronização protegidos", "A base local está pronta para sync 2.0 com adapter local/cloud.", "info", user.id, user.id, dedupe_key="sync-protected-demo")
    db.commit()
    return {"message": "Notificações geradas"}


@router.post("/{notification_id}/read")
def mark_notification_read(notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = mark_read(db, user, notification_id)
    if not item:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    db.commit()
    return item
