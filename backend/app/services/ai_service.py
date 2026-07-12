from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIProviderSetting, User
from app.services.tenant_service import ensure_enterprise_seed


def list_ai_providers(db: Session, user: User) -> list[dict]:
    ensure_enterprise_seed(db, user)
    rows = db.scalars(select(AIProviderSetting).where(AIProviderSetting.company_id == user.company_id, AIProviderSetting.deleted_at.is_(None)).order_by(AIProviderSetting.provider_type))
    return [{
        "id": item.id,
        "provider_type": item.provider_type,
        "provider_name": item.provider_name,
        "mode": item.mode,
        "endpoint_url": item.endpoint_url,
        "status": item.status,
    } for item in rows]
