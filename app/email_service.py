"""Servicio de envío de emails con adjunto.

Envía correos electrónicos con un fichero adjunto (normalmente un PDF) usando
SMTP con STARTTLS. Se usa para enviar facturas, consentimientos y justificantes
directamente al email del paciente desde la aplicación.

Variables de entorno requeridas (.env):
    SMTP_HOST     -> servidor SMTP (por defecto smtp.gmail.com).
    SMTP_PORT     -> puerto SMTP (por defecto 587).
    SMTP_USER     -> usuario/email de la cuenta remitente.
    SMTP_PASSWORD -> contraseña o app-password de la cuenta remitente.
    SMTP_FROM     -> dirección de email del remitente.
    CLINIC_NAME   -> nombre de la clínica (aparece como nombre del remitente).

Si SMTP_USER o SMTP_PASSWORD están vacíos, la función lanza ValueError.
"""
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
CLINIC_NAME = os.getenv("CLINIC_NAME", "Santé Fisioterapia")


def send_email_with_attachment(
    to_email: str,
    subject: str,
    body: str,
    attachment_path: str,
    attachment_filename: str | None = None,
) -> bool:
    """Envía un email con un PDF adjunto. Devuelve True si se envió correctamente."""
    if not SMTP_USER or not SMTP_PASSWORD:
        raise ValueError("Credenciales SMTP no configuradas en .env")

    msg = MIMEMultipart()
    msg["From"] = formataddr((CLINIC_NAME, SMTP_FROM))
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    filename = attachment_filename or os.path.basename(attachment_path)
    with open(attachment_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=filename)
    part["Content-Disposition"] = f'attachment; filename="{filename}"'
    msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

    return True
