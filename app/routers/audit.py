from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from app.auth import require_role
from app.db.database import get_db
from app.db.models import AuditLog, User, UserRole

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    user_id: int = Query(None),
    action: str = Query(None),
    entity_type: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if date_from:
        query = query.filter(AuditLog.created_at >= date.fromisoformat(date_from))
    if date_to:
        d = date.fromisoformat(date_to)
        from datetime import datetime, time
        query = query.filter(AuditLog.created_at <= datetime.combine(d, time(23, 59, 59)))

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return {
        "logs": [
            {
                "id": l.id,
                "user_name": l.user.full_name if l.user else "",
                "action": l.action,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "detail": l.detail,
                "created_at": l.created_at.isoformat() if l.created_at else "",
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "pages": (total + size - 1) // size,
    }


@router.get("/actions")
def list_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    rows = db.query(AuditLog.action).distinct().all()
    return [r[0] for r in rows]


@router.get("/entity-types")
def list_entity_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    rows = db.query(AuditLog.entity_type).distinct().all()
    return [r[0] for r in rows]
