import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal, DATABASE_URL
from app.db.models import Appointment, AppointmentStatus
from app.email_service import send_email_with_attachment, CLINIC_NAME

logger = logging.getLogger(__name__)

REMINDER_INTERVAL_SECONDS = 3600  # 1 hora

AUTO_BACKUP_PATH = os.getenv("AUTO_BACKUP_PATH", "C:/PoC/sante/backups")
DB_PATH = DATABASE_URL.replace("sqlite:///./", "")


def send_appointment_reminders():
    """Revisa citas de las próximas 24h y envía recordatorio por email."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(hours=24)

        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.start_time >= now,
                Appointment.start_time <= window_end,
                Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
                Appointment.reminder_sent == False,
            )
            .all()
        )

        for apt in appointments:
            patient = apt.patient
            if not patient or not patient.email:
                continue

            start_local = apt.start_time.strftime("%d-%m-%Y a las %H:%M")
            subject = f"Recordatorio de cita - {CLINIC_NAME}"
            body = (
                f"Hola {patient.first_name},\n\n"
                f"Le recordamos que tiene una cita programada el {start_local}.\n"
                f"Duración: {apt.duration_minutes} minutos.\n\n"
                f"Si necesita cancelar o modificar la cita, contacte con nosotros.\n\n"
                f"Un saludo,\n{CLINIC_NAME}"
            )

            try:
                # Usamos send_email sin adjunto (envío simple)
                _send_simple_email(patient.email, subject, body)
                apt.reminder_sent = True
                logger.info(f"Recordatorio enviado a {patient.email} para cita {apt.id}")
            except Exception as e:
                logger.error(f"Error enviando recordatorio cita {apt.id}: {e}")

        db.commit()
    except Exception as e:
        logger.error(f"Error en tarea de recordatorios: {e}")
    finally:
        db.close()


def _send_simple_email(to_email: str, subject: str, body: str):
    """Envía un email de texto plano sin adjunto."""
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from dotenv import load_dotenv

    from email.utils import formataddr

    load_dotenv()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", "")
    clinic_name = os.getenv("CLINIC_NAME", "Santé Fisioterapia")

    if not smtp_user or not smtp_password:
        raise ValueError("Credenciales SMTP no configuradas")

    msg = MIMEMultipart()
    msg["From"] = formataddr((clinic_name, smtp_from))
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


def auto_backup_db():
    """Copia de seguridad diaria de la BD. El día 1 del mes persiste una copia mensual."""
    import shutil
    os.makedirs(AUTO_BACKUP_PATH, exist_ok=True)
    if not os.path.exists(DB_PATH):
        logger.error(f"Auto-backup: BD no encontrada en {DB_PATH}")
        return
    today = datetime.now(timezone.utc) + timedelta(hours=2)
    # Copia mensual persistente el día 1
    if today.day == 1:
        monthly_name = f"sante_mensual_{today.strftime('%Y%m')}.db"
        monthly_path = os.path.join(AUTO_BACKUP_PATH, monthly_name)
        if not os.path.exists(monthly_path):
            shutil.copy2(DB_PATH, monthly_path)
            logger.info(f"Backup mensual creado: {monthly_name}")
    # Copia diaria (sobreescribe la anterior)
    daily_path = os.path.join(AUTO_BACKUP_PATH, "sante_diaria.db")
    shutil.copy2(DB_PATH, daily_path)
    logger.info("Backup diario actualizado")


def _reminder_loop():
    """Loop infinito que ejecuta recordatorios cada hora y backup a las 02:00."""
    while True:
        try:
            send_appointment_reminders()
        except Exception as e:
            logger.error(f"Error en loop de recordatorios: {e}")
        # Hora España (UTC+2)
        now_spain = datetime.now(timezone.utc) + timedelta(hours=2)
        if now_spain.hour == 2:
            try:
                auto_backup_db()
            except Exception as e:
                logger.error(f"Error en backup automático: {e}")
        time.sleep(REMINDER_INTERVAL_SECONDS)


def start_reminder_scheduler():
    """Inicia el hilo daemon para recordatorios."""
    thread = threading.Thread(target=_reminder_loop, daemon=True)
    thread.start()
    logger.info("Scheduler de recordatorios iniciado")
