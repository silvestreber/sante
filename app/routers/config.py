from datetime import date, datetime, timedelta
import os
import subprocess

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.db.database import get_db
from app.db.models import Appointment, AppointmentStatus, Config, Holiday, PhysioAbsence, PhysioSchedule, Schedule, SpecialSchedule, User, UserRole

router = APIRouter(prefix="/api/config", tags=["config"])

admin_only = require_role(UserRole.ADMIN)


# --- Schemas ---

class ScheduleItem(BaseModel):
    day_of_week: int
    morning_open: str | None = None
    morning_close: str | None = None
    afternoon_open: str | None = None
    afternoon_close: str | None = None
    is_closed: bool = False


class ScheduleBulk(BaseModel):
    schedules: list[ScheduleItem]


class SpecialScheduleCreate(BaseModel):
    name: str
    date_from: str  # YYYY-MM-DD
    date_to: str
    schedules: list[ScheduleItem]


class HolidayCreate(BaseModel):
    date: str  # YYYY-MM-DD
    name: str | None = None


class SettingsUpdate(BaseModel):
    default_duration: int | None = None
    default_session_price: float | None = None
    default_pack_price: float | None = None
    whatsapp_template: str | None = None


class ScheduleConflictCheck(BaseModel):
    schedules: list[ScheduleItem]
    date_from: str | None = None  # None = horario normal (desde ahora)
    date_to: str | None = None


# --- Helpers config ---

def get_config(db: Session, key: str, default: str = "") -> str:
    row = db.query(Config).filter(Config.key == key).first()
    return row.value if row else default


def set_config(db: Session, key: str, value: str):
    row = db.query(Config).filter(Config.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))



class PhysioScheduleItem(BaseModel):
    day_of_week: int
    morning_open: str | None = None
    morning_close: str | None = None
    afternoon_open: str | None = None
    afternoon_close: str | None = None
    is_off: bool = False


class PhysioScheduleBulk(BaseModel):
    user_id: int
    schedules: list[PhysioScheduleItem]


class PhysioAbsenceCreate(BaseModel):
    user_id: int
    date_from: str  # YYYY-MM-DD
    date_to: str
    time_from: str | None = None
    time_to: str | None = None
    reason: str | None = None


# --- Comprobación de citas fuera de horario ---

def _appointment_out_of_schedule(apt: Appointment, schedules_by_dow: dict) -> bool:
    """Devuelve True si la cita queda fuera del horario dado."""
    dow = apt.start_time.weekday()
    s = schedules_by_dow.get(dow)
    if not s:
        return False  # Sin configuración para ese día, no bloqueamos
    if s.get('is_closed'):
        return True
    start_str = apt.start_time.strftime("%H:%M")
    end_str = (apt.start_time + timedelta(minutes=apt.duration_minutes)).strftime("%H:%M")
    blocks = []
    if s.get('morning_open') and s.get('morning_close'):
        blocks.append((s['morning_open'], s['morning_close']))
    if s.get('afternoon_open') and s.get('afternoon_close'):
        blocks.append((s['afternoon_open'], s['afternoon_close']))
    if not blocks:
        return False
    return not any(start_str >= o and end_str <= c for o, c in blocks)


@router.post("/check-schedule-conflicts")
def check_schedule_conflicts(
    data: ScheduleConflictCheck,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedules_by_dow = {s.day_of_week: s.model_dump() for s in data.schedules}
    now = datetime.now()

    if data.date_from and data.date_to:
        # Horario especial: buscar solo en el rango
        date_from = datetime.fromisoformat(data.date_from)
        date_to = datetime.fromisoformat(data.date_to + "T23:59:59")
        query = db.query(Appointment).filter(
            Appointment.status != AppointmentStatus.CANCELLED,
            Appointment.start_time >= max(now, date_from),
            Appointment.start_time <= date_to,
        )
    else:
        # Horario normal: buscar desde ahora en adelante
        query = db.query(Appointment).filter(
            Appointment.status != AppointmentStatus.CANCELLED,
            Appointment.start_time >= now,
        )

    for apt in query.order_by(Appointment.start_time).all():
        if _appointment_out_of_schedule(apt, schedules_by_dow):
            return {
                "conflict": True,
                "appointment": {
                    "id": apt.id,
                    "start_time": apt.start_time.isoformat(),
                    "patient_name": f"{apt.patient.first_name} {apt.patient.last_name}" if apt.patient else "",
                }
            }
    return {"conflict": False}


# --- Horario normal ---

@router.get("/schedule")
def get_schedule(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(Schedule).order_by(Schedule.day_of_week).all()
    return [
        {
            "day_of_week": r.day_of_week,
            "morning_open": r.morning_open,
            "morning_close": r.morning_close,
            "afternoon_open": r.afternoon_open,
            "afternoon_close": r.afternoon_close,
            "is_closed": r.is_closed,
        }
        for r in rows
    ]


@router.put("/schedule")
def save_schedule(data: ScheduleBulk, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    db.query(Schedule).delete()
    for item in data.schedules:
        db.add(Schedule(
            day_of_week=item.day_of_week,
            morning_open=item.morning_open,
            morning_close=item.morning_close,
            afternoon_open=item.afternoon_open,
            afternoon_close=item.afternoon_close,
            is_closed=item.is_closed,
        ))
    db.commit()
    return {"message": "Horario guardado"}


# --- Horarios especiales ---

@router.get("/special-schedules")
def list_special_schedules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(SpecialSchedule).order_by(SpecialSchedule.date_from, SpecialSchedule.day_of_week).all()
    grouped = {}
    for r in rows:
        key = f"{r.name}|{r.date_from}|{r.date_to}"
        if key not in grouped:
            grouped[key] = {"id": r.id, "name": r.name, "date_from": r.date_from.isoformat(), "date_to": r.date_to.isoformat(), "schedules": []}
        grouped[key]["schedules"].append({
            "day_of_week": r.day_of_week,
            "morning_open": r.morning_open,
            "morning_close": r.morning_close,
            "afternoon_open": r.afternoon_open,
            "afternoon_close": r.afternoon_close,
            "is_closed": r.is_closed,
        })
    return list(grouped.values())


@router.post("/special-schedules", status_code=201)
def create_special_schedule(data: SpecialScheduleCreate, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    date_from = date.fromisoformat(data.date_from)
    date_to = date.fromisoformat(data.date_to)
    for item in data.schedules:
        db.add(SpecialSchedule(
            name=data.name.strip(),
            date_from=date_from,
            date_to=date_to,
            day_of_week=item.day_of_week,
            morning_open=item.morning_open,
            morning_close=item.morning_close,
            afternoon_open=item.afternoon_open,
            afternoon_close=item.afternoon_close,
            is_closed=item.is_closed,
        ))
    db.commit()
    return {"message": "Horario especial creado"}


@router.delete("/special-schedules/{name}")
def delete_special_schedule(name: str, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    deleted = db.query(SpecialSchedule).filter(SpecialSchedule.name == name).delete()
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="No encontrado")
    return {"message": "Horario especial eliminado"}


# --- Festivos ---

@router.get("/holidays")
def list_holidays(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(Holiday).order_by(Holiday.date).all()
    return [{"id": r.id, "date": r.date.isoformat(), "name": r.name} for r in rows]


@router.post("/holidays", status_code=201)
def create_holiday(data: HolidayCreate, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    d = date.fromisoformat(data.date)
    existing = db.query(Holiday).filter(Holiday.date == d).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un festivo en esa fecha")
    db.add(Holiday(date=d, name=data.name.strip() if data.name else None))
    db.commit()
    return {"message": "Festivo añadido"}


@router.delete("/holidays/{holiday_id}")
def delete_holiday(holiday_id: int, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    h = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(h)
    db.commit()
    return {"message": "Festivo eliminado"}


# --- Endpoint público para el calendario (consulta horario de un rango de fechas) ---

@router.get("/calendar-constraints")
def get_calendar_constraints(
    start: str,
    end: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve para cada día del rango: horario de apertura, bloques cerrados y festivos."""
    start_date = date.fromisoformat(start[:10])
    end_date = date.fromisoformat(end[:10])

    # Cargar datos
    normal_schedule = {s.day_of_week: s for s in db.query(Schedule).all()}
    specials = db.query(SpecialSchedule).filter(
        SpecialSchedule.date_from <= end_date,
        SpecialSchedule.date_to >= start_date,
    ).all()
    holidays = {h.date: h.name for h in db.query(Holiday).filter(
        Holiday.date >= start_date,
        Holiday.date <= end_date,
    ).all()}

    # Indexar especiales por (fecha_rango, day_of_week)
    special_map = {}
    for s in specials:
        special_map.setdefault((s.date_from, s.date_to), {})[s.day_of_week] = s

    result = {
        "holidays": [{"date": d.isoformat(), "name": n} for d, n in holidays.items()],
        "days": {},
        "slotMinTime": "06:00:00",
        "slotMaxTime": "22:00:00",
        "hiddenDays": [],  # Días de la semana siempre cerrados (0=domingo, 1=lunes... en FullCalendar)
    }

    # Detectar días siempre cerrados en horario normal
    for dow in range(7):
        sched = normal_schedule.get(dow)
        if sched and sched.is_closed:
            # FullCalendar usa 0=domingo, 1=lunes... convertir desde 0=lunes
            fc_dow = (dow + 1) % 7
            result["hiddenDays"].append(fc_dow)

    # Calcular min/max global para slotMinTime/slotMaxTime
    global_min = "23:59"
    global_max = "00:00"

    current = start_date
    while current <= end_date:
        dow = current.weekday()

        if current in holidays:
            result["days"][current.isoformat()] = {"closed": True, "name": holidays[current]}
            current += timedelta(days=1)
            continue

        # Buscar si hay horario especial para este día
        schedule = None
        for (df, dt), days_map in special_map.items():
            if df <= current <= dt and dow in days_map:
                schedule = days_map[dow]
                break

        if not schedule:
            schedule = normal_schedule.get(dow)

        if not schedule or schedule.is_closed:
            result["days"][current.isoformat()] = {"closed": True}
            current += timedelta(days=1)
            continue

        day_info = {"closed": False, "blocks": []}

        if schedule.morning_open and schedule.morning_close:
            day_info["blocks"].append({"open": schedule.morning_open, "close": schedule.morning_close})
            if schedule.morning_open < global_min:
                global_min = schedule.morning_open
            if schedule.morning_close > global_max:
                global_max = schedule.morning_close

        if schedule.afternoon_open and schedule.afternoon_close:
            day_info["blocks"].append({"open": schedule.afternoon_open, "close": schedule.afternoon_close})
            if schedule.afternoon_open < global_min:
                global_min = schedule.afternoon_open
            if schedule.afternoon_close > global_max:
                global_max = schedule.afternoon_close

        result["days"][current.isoformat()] = day_info
        current += timedelta(days=1)

    if global_min != "23:59":
        result["slotMinTime"] = global_min + ":00"
    if global_max != "00:00":
        result["slotMaxTime"] = global_max + ":00"
        result["closingTime"] = global_max

    return result


# --- Configuración general ---

DEFAULT_WHATSAPP = "Hola {nombre}, te recordamos que tienes cita en Santé Fisioterapia el {fecha} a las {hora}. Si no puedes asistir, por favor avísanos para cambiarla o cancelarla. ¡Gracias!"


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {
        "default_duration": int(get_config(db, "default_duration", "45")),
        "default_session_price": float(get_config(db, "default_session_price", "0")),
        "default_pack_price": float(get_config(db, "default_pack_price", "0")),
        "whatsapp_template": get_config(db, "whatsapp_template", DEFAULT_WHATSAPP),
    }


@router.put("/settings")
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    if data.default_duration is not None:
        set_config(db, "default_duration", str(data.default_duration))
    if data.default_session_price is not None:
        set_config(db, "default_session_price", str(data.default_session_price))
    if data.default_pack_price is not None:
        set_config(db, "default_pack_price", str(data.default_pack_price))
    if data.whatsapp_template is not None:
        set_config(db, "whatsapp_template", data.whatsapp_template.strip())
    db.commit()
    return {"message": "Configuración guardada"}


# --- Horarios de fisioterapeutas ---

@router.get("/physio-schedules/{user_id}")
def get_physio_schedule(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(PhysioSchedule).filter(PhysioSchedule.user_id == user_id).order_by(PhysioSchedule.day_of_week).all()
    return [
        {
            "day_of_week": r.day_of_week,
            "morning_open": r.morning_open,
            "morning_close": r.morning_close,
            "afternoon_open": r.afternoon_open,
            "afternoon_close": r.afternoon_close,
            "is_off": r.is_off,
        }
        for r in rows
    ]


@router.put("/physio-schedules")
def save_physio_schedule(data: PhysioScheduleBulk, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    db.query(PhysioSchedule).filter(PhysioSchedule.user_id == data.user_id).delete()
    for item in data.schedules:
        db.add(PhysioSchedule(
            user_id=data.user_id,
            day_of_week=item.day_of_week,
            morning_open=item.morning_open,
            morning_close=item.morning_close,
            afternoon_open=item.afternoon_open,
            afternoon_close=item.afternoon_close,
            is_off=item.is_off,
        ))
    db.commit()
    return {"message": "Horario del fisioterapeuta guardado"}


@router.get("/physio-schedules")
def list_all_physio_schedules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Devuelve horarios de todos los fisios para validación en frontend."""
    physios = db.query(User).filter(User.is_physio == True, User.is_active == True).all()
    result = {}
    for p in physios:
        rows = db.query(PhysioSchedule).filter(PhysioSchedule.user_id == p.id).all()
        result[str(p.id)] = {
            r.day_of_week: {
                "morning_open": r.morning_open,
                "morning_close": r.morning_close,
                "afternoon_open": r.afternoon_open,
                "afternoon_close": r.afternoon_close,
                "is_off": r.is_off,
            }
            for r in rows
        }
    return result


@router.post("/shutdown")
def shutdown_system(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Apaga el sistema de forma segura (solo Linux/Raspberry Pi)."""
    if os.name == "nt":
        subprocess.Popen(["shutdown", "/s", "/t", "5"], shell=True)
    else:
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])
    return {"message": "Apagando sistema..."}


# --- Ausencias de fisioterapeutas ---

@router.get("/physio-absences")
def list_all_physio_absences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve ausencias futuras de todos los fisios para validación en frontend."""
    today = date.today()
    rows = db.query(PhysioAbsence).filter(PhysioAbsence.date_to >= today).all()
    result = {}
    for r in rows:
        uid = str(r.user_id)
        if uid not in result:
            result[uid] = []
        result[uid].append({
            "date_from": r.date_from.isoformat(),
            "date_to": r.date_to.isoformat(),
            "time_from": r.time_from,
            "time_to": r.time_to,
            "reason": r.reason,
        })
    return result


@router.get("/physio-absences/{user_id}")
def list_physio_absences(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(PhysioAbsence).filter(
        PhysioAbsence.user_id == user_id
    ).order_by(PhysioAbsence.date_from.desc()).all()
    return [
        {
            "id": r.id,
            "date_from": r.date_from.isoformat(),
            "date_to": r.date_to.isoformat(),
            "time_from": r.time_from,
            "time_to": r.time_to,
            "reason": r.reason,
        }
        for r in rows
    ]


@router.post("/physio-absences", status_code=201)
def create_physio_absence(
    data: PhysioAbsenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    absence = PhysioAbsence(
        user_id=data.user_id,
        date_from=date.fromisoformat(data.date_from),
        date_to=date.fromisoformat(data.date_to),
        time_from=data.time_from,
        time_to=data.time_to,
        reason=data.reason.strip() if data.reason else None,
    )
    db.add(absence)
    db.commit()
    return {"id": absence.id, "message": "Ausencia registrada"}


@router.delete("/physio-absences/{absence_id}")
def delete_physio_absence(
    absence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    absence = db.query(PhysioAbsence).filter(PhysioAbsence.id == absence_id).first()
    if not absence:
        raise HTTPException(status_code=404, detail="Ausencia no encontrada")
    db.delete(absence)
    db.commit()
    return {"message": "Ausencia eliminada"}
