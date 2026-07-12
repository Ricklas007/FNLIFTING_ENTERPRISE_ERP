from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import InvalidTokenError, decode_token
from app.database.session import get_db
from app.models import Role, User, UserSession


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise unauthorized
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise unauthorized
        user_id, session_id = payload.get("sub"), payload.get("sid")
    except (InvalidTokenError, KeyError):
        raise unauthorized

    session = db.scalar(select(UserSession).where(UserSession.id == session_id))
    if not session or session.revoked_at or session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise unauthorized
    user = db.scalar(
        select(User)
        .options(selectinload(User.company), selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id, User.deleted_at.is_(None))
    )
    if not user or user.status != "active":
        raise unauthorized
    return user


def require_permission(*required: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        codes = user.permission_codes
        if "*" not in codes and not all(permission in codes for permission in required):
            raise HTTPException(status_code=403, detail="Não possui permissão para esta operação")
        return user
    return dependency
