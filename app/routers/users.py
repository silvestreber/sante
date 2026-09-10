from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import hash_password, require_role
from app.audit_log import log_action
from app.db.database import get_db
from app.db.models import User, UserRole

router = APIRouter(prefix="/api/users", tags=["users"])

admin_only = require_role(UserRole.ADMIN)


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: UserRole
    is_physio: bool = False
    is_colaborador: bool = False
    color: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    password: str | None = None
    is_physio: bool | None = None
    is_colaborador: bool | None = None
    color: str | None = None


@router.get("")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    users = db.query(User).order_by(User.full_name).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_physio": u.is_physio,
            "is_colaborador": u.is_colaborador,
            "is_active": u.is_active,
            "color": u.color,
        }
        for u in users
    ]


@router.post("", status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    if db.query(User).filter(User.username == data.username.strip().lower()).first():
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    user = User(
        username=data.username.strip().lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        role=data.role,
        is_physio=data.is_physio,
        is_colaborador=data.is_colaborador,
        color=data.color,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, current_user.id, "CREAR", "USUARIO", user.id, f"{user.username} ({user.role.value})")
    return {"id": user.id, "message": "Usuario creado"}


@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    if data.role is not None:
        user.role = data.role
    if data.is_physio is not None:
        user.is_physio = data.is_physio
    if data.is_colaborador is not None:
        user.is_colaborador = data.is_colaborador
    if data.color is not None:
        user.color = data.color if data.color else None
    if data.password:
        user.password_hash = hash_password(data.password)
    db.commit()
    log_action(db, current_user.id, "EDITAR", "USUARIO", user.id, user.username)
    return {"message": "Usuario actualizado"}


@router.patch("/{user_id}/deactivate")
def deactivate_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")
    user.is_active = not user.is_active
    db.commit()
    action = "ACTIVAR" if user.is_active else "DESACTIVAR"
    log_action(db, current_user.id, action, "USUARIO", user.id, user.username)
    return {"message": "Estado actualizado", "is_active": user.is_active}
