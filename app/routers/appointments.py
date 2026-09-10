import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.audit_log import log_action
from app.db.database import get_db
from app.db.models import (
    Appointment,
    AppointmentLocation,
    AppointmentStatus,
    ClinicalSession,
    Holiday,
    Patient,
    Schedule,
    SpecialSchedule,
    User,
    UserRole,
)

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


class AppointmentCreate(BaseModel):
    patient_id: int
    physio_id: int
    start_time: str  # ISO format
    duration_minutes: int = 30
    location: str = "CLINIC"
    notes: str | None = None
    force: bool = False


class AppointmentUpdate(BaseModel):
    start_time: str | None = None
    duration_minutes: int | None = None
    location: str | None = None
    status: str | None = None
    notes: str | None = None
    physio_id: int | None = None


class RecurrenceCreate(BaseModel):
    patient_id: int
    physio_id: int
    start_time: str  # ISO format of first occurrence
    duration_minutes: int = 30
    location: str = "CLINIC"
    notes: str | None = None
    days_of_week: list[int]  # 0=Monday ... 6=Sunday
    weeks: int = 4


def check_schedule(db: Session, start: datetime, duration: int):
    """Verifica que la cita cae dentro del horario de apertura y no en festivo."""
    day = start.date()
    end = start + timedelta(minutes=duration)

    # Festivo
    if db.query(Holiday).filter(Holiday.date == day).first():
        return "No se pueden crear citas en días festivos"

    # Buscar horario especial
    dow = day.weekday()
    special = db.query(SpecialSchedule).filter(
        SpecialSchedule.date_from <= day,
        SpecialSchedule.date_to >= day,
        SpecialSchedule.day_of_week == dow,
    ).first()

    schedule = special if special else db.query(Schedule).filter(Schedule.day_of_week == dow).first()

    if not schedule or schedule.is_closed:
        return "La clínica está cerrada en ese horario"

    # Verificar que la cita cae dentro de algún bloque abierto
    start_time = start.strftime("%H:%M")
    end_time = end.strftime("%H:%M")

    blocks = []
    if schedule.morning_open and schedule.morning_close:
        blocks.append((schedule.morning_open, schedule.morning_close))
    if schedule.afternoon_open and schedule.afternoon_close:
        blocks.append((schedule.afternoon_open, schedule.afternoon_close))

    if not blocks:
        return None  # No hay horario configurado, permitir

    for block_open, block_close in blocks:
        if start_time >= block_open and end_time <= block_close:
            return None  # Cita dentro de bloque válido

    return "La cita está fuera del horario de apertura"


def check_overlap(db: Session, physio_id: int, start: datetime, duration: int, exclude_id: int | None = None):
    end = start + timedelta(minutes=duration)
    query = db.query(Appointment).filter(
        Appointment.physio_id == physio_id,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.start_time < end,
        (Appointment.start_time + timedelta(minutes=1)) > start,  # placeholder
    )
    # SQLite doesn't support interval arithmetic, so we filter in Python
    appointments = db.query(Appointment).filter(
        Appointment.physio_id == physio_id,
        Appointment.status != AppointmentStatus.CANCELLED,
    ).all()

    for apt in appointments:
        if exclude_id and apt.id == exclude_id:
            continue
        apt_end = apt.start_time + timedelta(minutes=apt.duration_minutes)
        if start < apt_end and end > apt.start_time:
            return True
    return False


def appointment_to_dict(apt: Appointment, db: Session = None):
    has_session = False
    if db:
        has_session = db.query(ClinicalSession).filter(ClinicalSession.appointment_id == apt.id).first() is not None
    return {
        "id": apt.id,
        "patient_id": apt.patient_id,
        "patient_name": f"{apt.patient.first_name} {apt.patient.last_name}" if apt.patient else "",
        "physio_id": apt.physio_id,
        "physio_name": apt.physio.full_name if apt.physio else "",
        "start_time": apt.start_time.isoformat(),
        "duration_minutes": apt.duration_minutes,
        "location": apt.location.value if apt.location else "CLINIC",
        "status": apt.status.value if apt.status else "PENDING",
        "notes": apt.notes,
        "recurrence_group": apt.recurrence_group,
        "created_by": apt.created_by,
        "has_session": has_session,
    }


@router.get("")
def list_appointments(
    start: str = Query(...),
    end: str = Query(...),
    physio_id: int | None = Query(None),
    location: str | None = Query(None),
    patient_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Query params decode '+' as space, restore it
    start_dt = datetime.fromisoformat(start.replace(' ', '+'))
    end_dt = datetime.fromisoformat(end.replace(' ', '+'))

    query = db.query(Appointment).filter(
        Appointment.start_time >= start_dt,
        Appointment.start_time < end_dt,
    )
    if physio_id:
        query = query.filter(Appointment.physio_id == physio_id)
    if location:
        query = query.filter(Appointment.location == AppointmentLocation(location))
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)

    appointments = query.order_by(Appointment.start_time).all()
    return [appointment_to_dict(a, db) for a in appointments]


@router.post("", status_code=201)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    physio = db.query(User).filter(User.id == data.physio_id, User.is_physio == True, User.is_active == True).first()
    if not physio:
        raise HTTPException(status_code=404, detail="Fisioterapeuta no encontrado")

    start_dt = datetime.fromisoformat(data.start_time)

    schedule_error = check_schedule(db, start_dt, data.duration_minutes)
    if schedule_error and not data.force:
        raise HTTPException(status_code=409, detail=schedule_error)

    if check_overlap(db, data.physio_id, start_dt, data.duration_minutes):
        raise HTTPException(status_code=409, detail="Este fisio ya tiene ocupada esa hora")

    apt = Appointment(
        patient_id=data.patient_id,
        physio_id=data.physio_id,
        start_time=start_dt,
        duration_minutes=data.duration_minutes,
        location=AppointmentLocation(data.location),
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(apt)
    db.commit()
    db.refresh(apt)
    log_action(db, current_user.id, "CREAR", "CITA", apt.id, f"Paciente {data.patient_id}")
    return {"id": apt.id, "message": "Cita creada"}


@router.put("/{appointment_id}")
def update_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    if data.physio_id is not None:
        physio = db.query(User).filter(User.id == data.physio_id, User.is_physio == True, User.is_active == True).first()
        if not physio:
            raise HTTPException(status_code=404, detail="Fisioterapeuta no encontrado")
        apt.physio_id = data.physio_id

    new_start = datetime.fromisoformat(data.start_time) if data.start_time else apt.start_time
    new_duration = data.duration_minutes if data.duration_minutes else apt.duration_minutes

    if data.start_time or data.duration_minutes:
        if check_overlap(db, apt.physio_id, new_start, new_duration, exclude_id=apt.id):
            raise HTTPException(status_code=409, detail="Este fisio ya tiene ocupada esa hora")
        apt.start_time = new_start
        apt.duration_minutes = new_duration

    if data.location is not None:
        apt.location = AppointmentLocation(data.location)
    if data.status is not None:
        apt.status = AppointmentStatus(data.status)
    if data.notes is not None:
        apt.notes = data.notes

    db.commit()
    log_action(db, current_user.id, "EDITAR", "CITA", apt.id)
    return {"message": "Cita actualizada"}


@router.delete("/{appointment_id}")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    apt.status = AppointmentStatus.CANCELLED
    db.commit()
    log_action(db, current_user.id, "CANCELAR", "CITA", apt.id)
    return {"message": "Cita cancelada"}


@router.post("/recurrence", status_code=201)
def create_recurrence(
    data: RecurrenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    physio = db.query(User).filter(User.id == data.physio_id, User.is_physio == True, User.is_active == True).first()
    if not physio:
        raise HTTPException(status_code=404, detail="Fisioterapeuta no encontrado")

    first_start = datetime.fromisoformat(data.start_time)
    group_id = uuid.uuid4().hex
    created = []
    skipped = []

    # Generate dates for each week and each selected day
    for week in range(data.weeks):
        for day in data.days_of_week:
            # Calculate the date for this day in this week
            base_date = first_start.date() + timedelta(weeks=week)
            # Adjust to the correct day of week
            days_ahead = day - base_date.weekday()
            if week == 0 and days_ahead < 0:
                continue  # Skip days before the start date in first week
            target_date = base_date + timedelta(days=days_ahead)
            start_dt = datetime.combine(target_date, first_start.time())

            if check_overlap(db, data.physio_id, start_dt, data.duration_minutes):
                skipped.append(start_dt.isoformat())
                continue

            apt = Appointment(
                patient_id=data.patient_id,
                physio_id=data.physio_id,
                start_time=start_dt,
                duration_minutes=data.duration_minutes,
                location=AppointmentLocation(data.location),
                notes=data.notes,
                recurrence_group=group_id,
                created_by=current_user.id,
            )
            db.add(apt)
            created.append(start_dt.isoformat())

    db.commit()
    return {
        "message": f"{len(created)} citas creadas",
        "created": len(created),
        "skipped": len(skipped),
        "recurrence_group": group_id,
    }


@router.get("/physios")
def list_physios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    physios = db.query(User).filter(User.is_physio == True, User.is_active == True).all()
    return [{"id": p.id, "full_name": p.full_name, "color": p.color} for p in physios]
