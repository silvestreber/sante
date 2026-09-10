from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, verify_token
from app.db.database import get_db
from app.db.models import Notification, User
from app.websocket_manager import manager

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    recipient_id: int
    message: str


@router.get("")
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifications = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": n.id,
            "sender_name": n.sender.full_name if n.sender else "",
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else "",
        }
        for n in notifications
    ]


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(Notification)
        .filter(Notification.recipient_id == current_user.id, Notification.is_read == False)
        .count()
    )
    return {"count": count}


@router.post("", status_code=201)
async def send_notification(
    data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipient = db.query(User).filter(User.id == data.recipient_id, User.is_active == True).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Destinatario no encontrado")

    notification = Notification(
        sender_id=current_user.id,
        recipient_id=data.recipient_id,
        message=data.message,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    await manager.send_to_user(data.recipient_id, {
        "type": "new_notification",
        "id": notification.id,
        "sender_name": current_user.full_name,
        "message": data.message,
    })

    return {"message": "Aviso enviado"}


@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.recipient_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    notification.is_read = True
    db.commit()
    return {"message": "Marcada como leída"}


@router.put("/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.recipient_id == current_user.id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "Todas marcadas como leídas"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.recipient_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    db.delete(notification)
    db.commit()
    return {"message": "Notificación eliminada"}


@router.get("/users")
def list_users_for_notification(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    users = db.query(User).filter(User.is_active == True, User.id != current_user.id).all()
    return [{"id": u.id, "full_name": u.full_name, "role": u.role.value} for u in users]


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    await websocket.accept()
    if not token:
        await websocket.close(code=4001)
        return
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    user_id = payload.get("user_id")
    if user_id not in manager.active_connections:
        manager.active_connections[user_id] = []
    manager.active_connections[user_id].append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
