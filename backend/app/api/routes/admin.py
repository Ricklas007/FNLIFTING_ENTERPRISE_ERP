from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import Role, User
from app.schemas.auth import MessageResponse, UserOut
from app.api.routes.auth import user_out


router = APIRouter(prefix="/admin", tags=["Administração"])


@router.get("/users", response_model=list[UserOut])
def users(
    _current: User = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
):
    records = db.scalars(
        select(User)
        .options(selectinload(User.company), selectinload(User.roles).selectinload(Role.permissions))
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
    ).all()
    return [user_out(record) for record in records]


@router.post("/users/{user_id}/approve", response_model=MessageResponse)
def approve_user(
    user_id: str,
    _current: User = Depends(require_permission("users.approve")),
    db: Session = Depends(get_db),
):
    target = db.scalar(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    if not target:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    role = db.scalar(select(Role).where(Role.name == target.requested_role))
    if not role:
        raise HTTPException(status_code=422, detail="O perfil solicitado não está configurado")
    target.roles = [role]
    target.status = "active"
    if target.company.status == "pending":
        target.company.status = "active"
    db.commit()
    return MessageResponse(message="Conta aprovada com sucesso")

