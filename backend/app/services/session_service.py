from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserSession
from app.services.enterprise_utils import now_utc


def list_user_sessions(db: Session, user: User, limit: int = 30) -> list[dict]:
    rows = db.scalars(select(UserSession).where(UserSession.user_id == user.id).order_by(UserSession.created_at.desc()).limit(limit))
    return [{
        "id": row.id,
        "user_agent": row.user_agent,
        "ip_address": row.ip_address,
        "expires_at": row.expires_at,
        "revoked_at": row.revoked_at,
        "created_at": row.created_at,
        "status": "revoked" if row.revoked_at else "active",
    } for row in rows]


def revoke_user_session(db: Session, user: User, session_id: str) -> bool:
    session = db.scalar(select(UserSession).where(UserSession.id == session_id, UserSession.user_id == user.id))
    if not session:
        return False
    session.revoked_at = now_utc()
    return True
