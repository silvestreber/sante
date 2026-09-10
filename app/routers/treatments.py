from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.database import get_db
from app.db.models import Patient, Treatment, User

router = APIRouter(prefix="/api/treatments", tags=["treatments"])


class TreatmentCreate(BaseModel):
    patient_id: int
    title: str
    description: str


class TreatmentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


@router.get("/patient/{patient_id}")
def list_treatments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    treatments = db.query(Treatment).filter(
        Treatment.patient_id == patient_id
    ).order_by(Treatment.created_at.desc()).all()

    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "physio_name": t.physio.full_name if t.physio else "",
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in treatments
    ]


@router.post("", status_code=201)
def create_treatment(
    data: TreatmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    treatment = Treatment(
        patient_id=data.patient_id,
        physio_id=current_user.id,
        title=data.title.strip(),
        description=data.description.strip(),
    )
    db.add(treatment)
    db.commit()
    db.refresh(treatment)
    return {"id": treatment.id, "message": "Tratamiento creado"}


@router.get("/{treatment_id}")
def get_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    treatment = db.query(Treatment).filter(Treatment.id == treatment_id).first()
    if not treatment:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")

    return {
        "id": treatment.id,
        "patient_id": treatment.patient_id,
        "title": treatment.title,
        "description": treatment.description,
        "physio_name": treatment.physio.full_name if treatment.physio else "",
        "created_at": treatment.created_at.isoformat() if treatment.created_at else None,
    }


@router.put("/{treatment_id}")
def update_treatment(
    treatment_id: int,
    data: TreatmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    treatment = db.query(Treatment).filter(Treatment.id == treatment_id).first()
    if not treatment:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")

    if data.title is not None:
        treatment.title = data.title.strip()
    if data.description is not None:
        treatment.description = data.description.strip()

    db.commit()
    return {"message": "Tratamiento actualizado"}


@router.delete("/{treatment_id}")
def delete_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    treatment = db.query(Treatment).filter(Treatment.id == treatment_id).first()
    if not treatment:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")

    db.delete(treatment)
    db.commit()
    return {"message": "Tratamiento eliminado"}
