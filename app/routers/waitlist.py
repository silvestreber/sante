from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.database import get_db
from app.db.models import Patient, User, WaitlistEntry, WaitlistTimePreference

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])


class WaitlistCreate(BaseModel):
    patient_id: int
    physio_ids: list[int] | None = None
    time_preference: WaitlistTimePreference = WaitlistTimePreference.ANY
    time_from: str | None = None
    time_to: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    asap: bool = False
    priority: bool = False
    notes: str | None = None


@router.get("")
def list_waitlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entries = (
        db.query(WaitlistEntry)
        .filter(WaitlistEntry.is_resolved == False)
        .order_by(
            WaitlistEntry.date_from.asc().nullsfirst(),
            WaitlistEntry.priority.desc(),
            WaitlistEntry.created_at.asc(),
        )
        .all()
    )

    # Load physio names
    physio_map = {}
    physios = db.query(User).filter(User.is_physio == True, User.is_active == True).all()
    for p in physios:
        physio_map[str(p.id)] = p.full_name

    return [
        {
            "id": e.id,
            "patient_id": e.patient_id,
            "patient_name": f"{e.patient.first_name} {e.patient.last_name}" if e.patient else "",
            "patient_phone": e.patient.phone if e.patient else "",
            "physio_ids": e.physio_ids.split(",") if e.physio_ids else [],
            "physio_names": [physio_map.get(pid, "") for pid in e.physio_ids.split(",") if pid] if e.physio_ids else [],
            "time_preference": e.time_preference.value,
            "time_from": e.time_from,
            "time_to": e.time_to,
            "date_from": e.date_from.isoformat() if e.date_from else None,
            "date_to": e.date_to.isoformat() if e.date_to else None,
            "asap": e.asap,
            "priority": e.priority,
            "notes": e.notes,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.post("", status_code=201)
def create_waitlist_entry(
    data: WaitlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    entry = WaitlistEntry(
        patient_id=data.patient_id,
        physio_ids=",".join(str(pid) for pid in data.physio_ids) if data.physio_ids else None,
        time_preference=data.time_preference,
        time_from=data.time_from,
        time_to=data.time_to,
        date_from=date.fromisoformat(data.date_from) if data.date_from else None,
        date_to=date.fromisoformat(data.date_to) if data.date_to else None,
        asap=data.asap,
        priority=data.priority,
        notes=data.notes.strip() if data.notes else None,
        created_by=current_user.id,
    )
    db.add(entry)
    db.commit()
    return {"id": entry.id, "message": "Añadido a lista de espera"}


@router.put("/{entry_id}/resolve")
def resolve_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.query(WaitlistEntry).filter(WaitlistEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    entry.is_resolved = True
    db.commit()
    return {"message": "Marcada como resuelta"}


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.query(WaitlistEntry).filter(WaitlistEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    db.delete(entry)
    db.commit()
    return {"message": "Entrada eliminada"}


@router.delete("/patient/{patient_id}")
def delete_patient_entries(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(WaitlistEntry).filter(
        WaitlistEntry.patient_id == patient_id,
        WaitlistEntry.is_resolved == False,
    ).delete()
    db.commit()
    return {"message": "Entradas del paciente eliminadas"}


@router.get("/check-slot")
def check_slot_matches(
    start_time: str = "",
    physio_id: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca pacientes en lista de espera que encajen con un hueco liberado."""
    from datetime import datetime
    if not start_time or not physio_id:
        return []

    dt = datetime.fromisoformat(start_time)
    slot_date = dt.date()
    slot_time = dt.strftime("%H:%M")
    slot_hour = dt.hour

    entries = (
        db.query(WaitlistEntry)
        .filter(WaitlistEntry.is_resolved == False)
        .order_by(
            WaitlistEntry.date_from.asc().nullsfirst(),
            WaitlistEntry.priority.desc(),
            WaitlistEntry.created_at.asc(),
        )
        .all()
    )

    matches = []
    for e in entries:
        # Check physio preference
        if e.physio_ids:
            if str(physio_id) not in e.physio_ids.split(","):
                continue

        # Check date preference
        if e.date_from and slot_date < e.date_from:
            continue
        if e.date_to and slot_date > e.date_to:
            continue

        # Check time preference
        if e.time_preference == WaitlistTimePreference.MORNING and slot_hour >= 14:
            continue
        if e.time_preference == WaitlistTimePreference.AFTERNOON and slot_hour < 14:
            continue
        if e.time_preference == WaitlistTimePreference.CUSTOM:
            if e.time_from and slot_time < e.time_from:
                continue
            if e.time_to and slot_time > e.time_to:
                continue

        matches.append({
            "id": e.id,
            "patient_id": e.patient_id,
            "patient_name": f"{e.patient.first_name} {e.patient.last_name}" if e.patient else "",
            "patient_phone": e.patient.phone if e.patient else "",
            "priority": e.priority,
        })

    return matches


@router.get("/patient/{patient_id}/pending")
def patient_has_pending(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(WaitlistEntry)
        .filter(WaitlistEntry.patient_id == patient_id, WaitlistEntry.is_resolved == False)
        .count()
    )
    return {"count": count}
