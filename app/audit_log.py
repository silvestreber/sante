from sqlalchemy.orm import Session

from app.db.models import AuditLog


def log_action(db: Session, user_id: int, action: str, entity_type: str, entity_id: int = None, detail: str = None):
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(entry)
    db.commit()
