from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import create_token, verify_password
from app.db.database import get_db
from app.db.models import User

security = HTTPBearer()

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str
    full_name: str
    is_physio: bool
    user_id: int


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username.lower()).first()
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    token = create_token(user.id, user.username, user.role.value)
    return LoginResponse(token=token, role=user.role.value, full_name=user.full_name, is_physio=user.is_physio, user_id=user.id)


class VerifyPasswordRequest(BaseModel):
    password: str


@router.post("/verify-password")
def verify_user_password(
    data: VerifyPasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    from app.auth import decode_token
    payload = decode_token(credentials.credentials)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contrase\u00f1a incorrecta")
    return {"message": "OK"}
