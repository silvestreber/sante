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
        })

    return {"sessions": result}


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
