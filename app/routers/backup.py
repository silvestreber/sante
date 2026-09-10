import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role, verify_password
from app.db.database import DATABASE_URL, SessionLocal, engine
from app.db.models import User, UserRole

router = APIRouter(prefix="/api/backup", tags=["backup"])

admin_only = require_role(UserRole.ADMIN)

DB_PATH = DATABASE_URL.replace("sqlite:///./", "")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")


class PasswordCheck(BaseModel):
    password: str


@router.post("/export")
def export_backup(
    body: PasswordCheck,
    current_user: User = Depends(admin_only),
):
    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Contraseña incorrecta")

    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Base de datos no encontrada")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"sante_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    shutil.copy2(DB_PATH, backup_path)

    return FileResponse(
        backup_path,
        media_type="application/octet-stream",
        filename=backup_filename,
    )


@router.post("/import")
async def import_backup(
    password: str,
    file: UploadFile = File(...),
    current_user: User = Depends(admin_only),
):
    if not verify_password(password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Contraseña incorrecta")

    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .db")

    # Guardar copia de seguridad del actual antes de reemplazar
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pre_restore_path = os.path.join(BACKUP_DIR, f"sante_pre_restore_{timestamp}.db")
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, pre_restore_path)

    # Cerrar conexiones activas
    engine.dispose()

    # Escribir el archivo subido como nueva DB
    try:
        content = await file.read()
        with open(DB_PATH, "wb") as f:
            f.write(content)
    except Exception as e:
        # Restaurar la copia anterior si falla
        if os.path.exists(pre_restore_path):
            shutil.copy2(pre_restore_path, DB_PATH)
        raise HTTPException(status_code=500, detail=f"Error al restaurar: {str(e)}")

    return {"message": "Copia de seguridad restaurada correctamente"}
