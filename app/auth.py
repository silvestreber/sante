"""Autenticación y autorización de la aplicación.

Implementa autenticación basada en JWT (JSON Web Tokens) con sesión deslizante:
el token expira a los 30 minutos de INACTIVIDAD (no de emisión). El frontend
debe llamar a POST /api/auth/refresh periódicamente mientras haya actividad.

Flujo de autenticación:
    1. El cliente llama a POST /api/auth/login con usuario y contraseña.
    2. El servidor devuelve un JWT firmado con SECRET_KEY (HS256).
    3. El cliente incluye el token en la cabecera: Authorization: Bearer <token>.
    4. Cada endpoint protegido usa get_current_user() como dependencia FastAPI.

Roles disponibles (UserRole):
    ADMIN      -> acceso total, gestión de usuarios y configuración.
    RECEPTION  -> gestión de citas, pacientes y facturación.
    PHYSIO     -> acceso clínico (historial, sesiones, tratamientos).

Variables de entorno:
    SECRET_KEY -> clave de firma JWT. CAMBIAR en producción.
"""
from datetime import datetime, timedelta, timezone
from typing import List

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, UserRole

import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "clave-secreta-cambiar-en-produccion")
ALGORITHM = "HS256"
# Sesión deslizante: el token vive 30 minutos y se refresca con la actividad.
# El usuario solo es expulsado tras 30 minutos de inactividad.
TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()


def hash_password(password: str) -> str:
    """Genera un hash bcrypt de la contraseña en texto plano."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba si una contraseña en texto plano coincide con su hash bcrypt."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(user_id: int, username: str, role: str) -> str:
    """Genera un JWT firmado con los datos del usuario.

    El token incluye: sub (user_id), username, role y exp (expiración).
    Expira en TOKEN_EXPIRE_MINUTES minutos desde su creación.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica y valida un JWT. Lanza HTTP 401 si el token es inválido o ha expirado."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


def verify_token(token: str) -> dict | None:
    """Verifica un token sin lanzar excepción. Devuelve payload con user_id o None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"user_id": int(payload["sub"]), "role": payload.get("role")}
    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Dependencia FastAPI que extrae y valida el usuario del token JWT.

    Uso: `current_user: User = Depends(get_current_user)` en cualquier endpoint.
    Lanza HTTP 401 si el token es inválido o el usuario está desactivado.
    """
    payload = decode_token(credentials.credentials)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no válido")
    return user


def require_role(*roles: UserRole):
    """Factoria de dependencias que restringe el acceso a uno o varios roles.

    Ejemplo de uso:
        @router.get("/admin-only")
        def endpoint(user = Depends(require_role(UserRole.ADMIN))):
            ...

    Lanza HTTP 403 si el usuario autenticado no tiene ninguno de los roles indicados.
    """
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos")
        return current_user
    return dependency


def require_physio(current_user: User = Depends(get_current_user)):
    """Permite acceso a cualquier usuario con is_physio=True, independientemente del rol."""
    if not current_user.is_physio:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos de fisioterapeuta")
    return current_user
