"""Router de historial clínico y sesiones.

Endpoints:
    GET  /api/clinical/patient/{id}  -> historial completo de sesiones de un paciente
                                        (incluye info de pago, bono y duración).
    POST /api/clinical/sessions      -> registra una sesión clínica vinculada a una cita.
    POST /api/clinical/sessions/manual -> registra una sesión manual (sin cita asociada,
                                          para sesiones anteriores o externas a la clínica).
    PUT  /api/clinical/sessions/{id} -> actualiza las observaciones de una sesión.

Sesiones manuales (is_manual=True):
    No tienen appointment_id. Se usan para incorporar al historial sesiones que
    no pasaron por el sistema (p.ej. tratamientos previos). No se puede emitir
    justificante de asistencia para estas sesiones.

Fecha de la sesión:
    Al crear una sesión vinculada a una cita, la fecha se toma de la cita
    (appointment.start_time), no de la fecha actual. Así el historial refleja
    cuándo se realizó la sesión, no cuándo se registró.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_physio
from app.audit_log import log_action
from app.db.database import get_db
from app.db.models import (
    Appointment,
    ClinicalSession,
    Patient,
    User,
)

router = APIRouter(prefix="/api/clinical", tags=["clinical"])


class SessionCreate(BaseModel):
    patient_id: int
    appointment_id: int
    observations: str | None = None


class SessionUpdate(BaseModel):
    observations: str | None = None


class ManualSessionCreate(BaseModel):
    patient_id: int
    date: datetime  # fecha/hora de la sesión (ISO). Puede ser pasada.
    observations: str | None = None
    physio_id: int | None = None  # opcional; si no se indica, el usuario actual


@router.get("/patient/{patient_id}")
def get_patient_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.db.models import Invoice
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    sessions = db.query(ClinicalSession).filter(
        ClinicalSession.patient_id == patient_id
    ).order_by(ClinicalSession.date.desc()).all()

    result = []
    for s in sessions:
        # Buscar si la cita asociada tiene documento de cobro
        invoice = db.query(Invoice).filter(Invoice.appointment_id == s.appointment_id).first() if s.appointment_id else None
        # Buscar si se pago con bono
        paid_with_pack = invoice.session_pack_id is not None if invoice else False
        appointment = db.query(Appointment).filter(Appointment.id == s.appointment_id).first() if s.appointment_id else None
        result.append({
            "id": s.id,
            "date": s.date.isoformat() if s.date else None,
            "physio_name": s.physio.full_name if s.physio else "",
            "observations": s.observations,
            "appointment_id": s.appointment_id,
            "payment_method": invoice.payment_method.value if invoice and invoice.payment_method else None,
            "paid_with_pack": paid_with_pack,
            "is_paid": invoice.is_paid if invoice else False,
            "invoice_id": invoice.id if invoice else None,
            "duration_minutes": appointment.duration_minutes if appointment else None,
            "is_manual": bool(s.is_manual),
            "is_future": False,
        })

    # Citas futuras (programadas, aún no realizadas): se muestran en el historial
    # como informativas. No son sesiones, así que NO permiten editar seguimiento,
    # justificante de asistencia ni cobro desde aquí. Se excluyen las canceladas,
    # las ya finalizadas y las que ya tienen una sesión clínica registrada.
    from app.db.models import AppointmentStatus
    now = datetime.now()
    future_appts = db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.start_time >= now,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.status != AppointmentStatus.FINALIZED,
    ).order_by(Appointment.start_time.asc()).all()

    for apt in future_appts:
        # Evitar duplicar si ya existe una sesión clínica para esa cita.
        has_session = db.query(ClinicalSession).filter(
            ClinicalSession.appointment_id == apt.id
        ).first() is not None
        if has_session:
            continue
        result.append({
            "id": None,
            "appointment_id": apt.id,
            "date": apt.start_time.isoformat() if apt.start_time else None,
            "physio_name": apt.physio.full_name if apt.physio else "",
            "observations": apt.notes,
            "duration_minutes": apt.duration_minutes,
            "status": apt.status.value if apt.status else "PENDING",
            "payment_method": None,
            "paid_with_pack": False,
            "is_paid": False,
            "invoice_id": None,
            "is_manual": False,
            "is_future": True,
        })

    return {"sessions": result}


@router.post("/sessions/manual", status_code=201)
def create_manual_session(
    data: ManualSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra en el historial una sesión anterior o externa a la clínica, sin cita
    asociada. Útil para incorporar sesiones no registradas en el sistema."""
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    physio_id = data.physio_id if data.physio_id is not None else current_user.id
    if data.physio_id is not None:
        physio = db.query(User).filter(User.id == data.physio_id).first()
        if not physio:
            raise HTTPException(status_code=404, detail="Fisioterapeuta no encontrado")

    session = ClinicalSession(
        patient_id=data.patient_id,
        appointment_id=None,
        physio_id=physio_id,
        observations=data.observations,
        date=data.date,
        is_manual=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    log_action(db, current_user.id, "CREAR", "SESION_MANUAL", session.id, f"Paciente {data.patient_id}")
    return {"id": session.id, "message": "Sesion manual registrada"}


@router.post("/sessions", status_code=201)
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Usar la fecha/hora de la cita, no la actual
    appointment = db.query(Appointment).filter(Appointment.id == data.appointment_id).first()
    session_date = appointment.start_time if appointment else datetime.now(timezone.utc)

    session = ClinicalSession(
        patient_id=data.patient_id,
        appointment_id=data.appointment_id,
        physio_id=current_user.id,
        observations=data.observations,
        date=session_date,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    log_action(db, current_user.id, "CREAR", "SESION_CLINICA", session.id, f"Paciente {data.patient_id}")
    return {"id": session.id, "message": "Sesion registrada"}


@router.put("/sessions/{session_id}")
def update_session(
    session_id: int,
    data: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ClinicalSession).filter(ClinicalSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")

    if data.observations is not None:
        session.observations = data.observations

    db.commit()
    return {"message": "Sesion actualizada"}
