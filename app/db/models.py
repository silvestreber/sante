import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class EntryType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"



class DocType(str, enum.Enum):
    INVOICE = "INVOICE"
    SIMPLIFIED_INVOICE = "SIMPLIFIED_INVOICE"
    RECEIPT = "RECEIPT"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    BIZUM = "BIZUM"


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    RECEPTION = "RECEPTION"
    PHYSIO = "PHYSIO"


class AppointmentLocation(str, enum.Enum):
    CLINIC = "CLINIC"
    HOME = "HOME"


class AppointmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    FINALIZED = "FINALIZED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_physio = Column(Boolean, default=False)
    is_colaborador = Column(Boolean, default=False)
    color = Column(String, nullable=True)  # Color hex para calendario
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    dni = Column(String, nullable=True)
    allergies = Column(Text, nullable=True)  # legacy, no se usa en formulario
    notes = Column(Text, nullable=True)  # legacy, no se usa en formulario
    motivo_consulta = Column(Text, nullable=True)
    anamnesis = Column(Text, nullable=True)
    tratamiento_contraindicaciones = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    documents = relationship("PatientDocument", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient")
    sessions = relationship("ClinicalSession", back_populates="patient")
    treatments = relationship("Treatment", back_populates="patient", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="patient", cascade="all, delete-orphan")
    session_packs = relationship("SessionPack", back_populates="patient", cascade="all, delete-orphan")


class PatientDocument(Base):
    __tablename__ = "patient_documents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    description = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="documents")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    physio_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=30)
    location = Column(Enum(AppointmentLocation), nullable=False, default=AppointmentLocation.CLINIC)
    status = Column(Enum(AppointmentStatus), nullable=False, default=AppointmentStatus.PENDING)
    notes = Column(Text, nullable=True)
    recurrence_group = Column(String, nullable=True)
    reminder_sent = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="appointments")
    physio = relationship("User", foreign_keys=[physio_id])
    creator = relationship("User", foreign_keys=[created_by])


class ClinicalSession(Base):
    __tablename__ = "clinical_sessions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    physio_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    observations = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="sessions")
    appointment = relationship("Appointment")
    physio = relationship("User", foreign_keys=[physio_id])


class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    physio_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="treatments")
    physio = relationship("User", foreign_keys=[physio_id])





class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    session_pack_id = Column(Integer, ForeignKey("session_packs.id"), nullable=True)
    invoice_number = Column(String, unique=True, nullable=False)
    doc_type = Column(Enum(DocType), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    is_paid = Column(Boolean, default=False)
    pdf_filename = Column(String, nullable=True)  # nombre relativo del PDF (base en Config)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="invoices")
    appointment = relationship("Appointment", foreign_keys=[appointment_id])
    session_pack = relationship("SessionPack", foreign_keys=[session_pack_id])


class SessionPack(Base):
    __tablename__ = "session_packs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    total_sessions = Column(Integer, nullable=False)
    used_sessions = Column(Integer, default=0)
    price = Column(Float, nullable=False)
    is_cancelled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(Date, nullable=True)

    patient = relationship("Patient", back_populates="session_packs")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])


class FinanceEntry(Base):
    __tablename__ = "finance_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_type = Column(Enum(EntryType), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    creator = relationship("User", foreign_keys=[created_by])
    invoice = relationship("Invoice", foreign_keys=[invoice_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id])


class Schedule(Base):
    """Horario normal semanal. Un registro por día de la semana (0=Lunes..6=Domingo)."""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    morning_open = Column(String, nullable=True)   # HH:MM
    morning_close = Column(String, nullable=True)  # HH:MM
    afternoon_open = Column(String, nullable=True)  # HH:MM
    afternoon_close = Column(String, nullable=True) # HH:MM
    is_closed = Column(Boolean, default=False)


class SpecialSchedule(Base):
    """Horario especial para periodos concretos."""
    __tablename__ = "special_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Ej: "Horario verano"
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    morning_open = Column(String, nullable=True)
    morning_close = Column(String, nullable=True)
    afternoon_open = Column(String, nullable=True)
    afternoon_close = Column(String, nullable=True)
    is_closed = Column(Boolean, default=False)


class Holiday(Base):
    """Días festivos (clínica cerrada)."""
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True)
    name = Column(String, nullable=True)  # Ej: "Navidad"


class Config(Base):
    """Configuración general clave-valor."""
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)


class PhysioAbsence(Base):
    """Ausencias y vacaciones de fisioterapeutas."""
    __tablename__ = "physio_absences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    time_from = Column(String, nullable=True)  # HH:MM, null = día completo
    time_to = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id])


class WaitlistTimePreference(str, enum.Enum):
    ANY = "ANY"
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    CUSTOM = "CUSTOM"


class PhysioSchedule(Base):
    """Horario personal de cada fisioterapeuta."""
    __tablename__ = "physio_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    morning_open = Column(String, nullable=True)   # HH:MM
    morning_close = Column(String, nullable=True)  # HH:MM
    afternoon_open = Column(String, nullable=True)  # HH:MM
    afternoon_close = Column(String, nullable=True) # HH:MM
    is_off = Column(Boolean, default=False)

    user = relationship("User", foreign_keys=[user_id])


class WaitlistEntry(Base):
    """Lista de espera de pacientes que buscan cita."""
    __tablename__ = "waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    physio_ids = Column(String, nullable=True)  # Comma-separated IDs, None = cualquiera
    time_preference = Column(Enum(WaitlistTimePreference), default=WaitlistTimePreference.ANY)
    time_from = Column(String, nullable=True)  # HH:MM - solo si CUSTOM
    time_to = Column(String, nullable=True)    # HH:MM - solo si CUSTOM
    date_from = Column(Date, nullable=True)    # Desde qué fecha le vale
    date_to = Column(Date, nullable=True)      # Hasta qué fecha le vale
    asap = Column(Boolean, default=False)      # Lo antes posible
    priority = Column(Boolean, default=False)  # Prioritario
    notes = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", foreign_keys=[patient_id])
    creator = relationship("User", foreign_keys=[created_by])

