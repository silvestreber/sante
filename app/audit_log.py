"""Utilidad para registrar acciones de auditoría en la base de datos.

Cada vez que un usuario realiza una acción relevante (crear, editar, eliminar
un paciente, cita, factura, etc.) se llama a log_action() para dejar traza.
Los registros se almacenan en la tabla `audit_logs` y son consultables desde
el panel de auditoría (solo ADMIN).

Ejemplo de uso:
    log_action(db, current_user.id, "CREAR", "PACIENTE", patient.id, "Juan Garcia")
"""
from sqlalchemy.orm import Session

from app.db.models import AuditLog


def log_action(db: Session, user_id: int, action: str, entity_type: str, entity_id: int = None, detail: str = None):
    """Registra una acción de auditoría en la tabla audit_logs.

    Args:
        db:          Sesión de base de datos activa.
        user_id:     ID del usuario que realiza la acción.
        action:      Verbo de la acción (ej: "CREAR", "EDITAR", "ELIMINAR", "CANCELAR").
        entity_type: Tipo de entidad afectada (ej: "PACIENTE", "CITA", "FACTURA").
        entity_id:   ID del registro afectado (opcional).
        detail:      Información adicional en texto libre (opcional).
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(entry)
    db.commit()
