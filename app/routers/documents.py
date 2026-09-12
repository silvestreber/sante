import os
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.consent_generator import MESES
from app.db.database import get_db
from app.db.models import Invoice, Patient, PatientDocument, Treatment, User
from app.email_service import send_email_with_attachment
from app.pdf import (
    generate_attendance_pdf,
    generate_consent_pdf,
    generate_invoice_pdf,
    generate_treatment_pdf,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


class EmailRequest(BaseModel):
    email: str | None = None


# --- Invoice PDF ---

@router.get("/invoice/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    patient = db.query(Patient).filter(Patient.id == invoice.patient_id).first()

    data = {
        "invoice_number": invoice.invoice_number,
        "doc_type": invoice.doc_type.value,
        "amount": invoice.amount,
        "description": (invoice.appointment.start_time.strftime("%d-%m-%Y %H:%M") if invoice.appointment else (f"Bono {invoice.session_pack.total_sessions} sesiones" if invoice.session_pack else "")),
        "payment_method": invoice.payment_method.value if invoice.payment_method else None,
        "is_paid": invoice.is_paid,
        "date": invoice.created_at.strftime("%d-%m-%Y") if invoice.created_at else None,
        "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "",
        "patient_dni": patient.dni if patient else "",
    }
    path = generate_invoice_pdf(data)
    filename = f"{invoice.invoice_number}.pdf"
    return FileResponse(path, filename=filename, media_type="application/pdf")


@router.post("/invoice/{invoice_id}/email")
def email_invoice(
    invoice_id: int,
    body: EmailRequest = EmailRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    patient = db.query(Patient).filter(Patient.id == invoice.patient_id).first()

    to_email = body.email or (patient.email if patient else None)
    if not to_email:
        raise HTTPException(status_code=400, detail="El paciente no tiene email registrado")

    data = {
        "invoice_number": invoice.invoice_number,
        "doc_type": invoice.doc_type.value,
        "amount": invoice.amount,
        "description": (invoice.appointment.start_time.strftime("%d-%m-%Y %H:%M") if invoice.appointment else (f"Bono {invoice.session_pack.total_sessions} sesiones" if invoice.session_pack else "")),
        "payment_method": invoice.payment_method.value if invoice.payment_method else None,
        "is_paid": invoice.is_paid,
        "date": invoice.created_at.strftime("%d-%m-%Y") if invoice.created_at else None,
        "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "",
        "patient_dni": patient.dni if patient else "",
    }
    path = generate_invoice_pdf(data)

    type_labels = {"INVOICE": "Factura", "SIMPLIFIED_INVOICE": "Factura simplificada", "RECEIPT": "Justificante"}
    doc_label = type_labels.get(invoice.doc_type.value, "Documento")

    try:
        send_email_with_attachment(
            to_email=to_email,
            subject=f"{doc_label} {invoice.invoice_number} - {os.getenv('CLINIC_NAME', 'Santé')}",
            body=f"Adjunto encontrará su {doc_label.lower()} nº {invoice.invoice_number}.\n\nUn saludo,\n{os.getenv('CLINIC_NAME', 'Santé Fisioterapia')}",
            attachment_path=path,
            attachment_filename=f"{invoice.invoice_number}.pdf",
        )
    except Exception as e:
        logging.error(f"Error enviando email: {e}")
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")
    finally:
        _cleanup(path)

    return {"message": f"Email enviado a {to_email}"}


# --- Treatment PDF ---

@router.get("/treatment/{treatment_id}/pdf")
def download_treatment_pdf(
    treatment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    treatment = db.query(Treatment).filter(Treatment.id == treatment_id).first()
    if not treatment:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")
    patient = db.query(Patient).filter(Patient.id == treatment.patient_id).first()

    data = {
        "title": treatment.title,
        "description": treatment.description,
        "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "",
        "physio_name": treatment.physio.full_name if treatment.physio else "",
        "date": treatment.created_at.strftime("%d-%m-%Y") if treatment.created_at else None,
    }
    path = generate_treatment_pdf(data)
    return FileResponse(path, filename=f"tratamiento_{treatment_id}.pdf", media_type="application/pdf")


@router.post("/treatment/{treatment_id}/email")
def email_treatment(
    treatment_id: int,
    body: EmailRequest = EmailRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    treatment = db.query(Treatment).filter(Treatment.id == treatment_id).first()
    if not treatment:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")
    patient = db.query(Patient).filter(Patient.id == treatment.patient_id).first()

    to_email = body.email or (patient.email if patient else None)
    if not to_email:
        raise HTTPException(status_code=400, detail="El paciente no tiene email registrado")

    data = {
        "title": treatment.title,
        "description": treatment.description,
        "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "",
        "physio_name": treatment.physio.full_name if treatment.physio else "",
        "date": treatment.created_at.strftime("%d-%m-%Y") if treatment.created_at else None,
    }
    path = generate_treatment_pdf(data)

    try:
        send_email_with_attachment(
            to_email=to_email,
            subject=f"Tratamiento: {treatment.title} - {os.getenv('CLINIC_NAME', 'Santé')}",
            body=f"Adjunto encontrará su plan de tratamiento/ejercicios.\n\nUn saludo,\n{os.getenv('CLINIC_NAME', 'Santé Fisioterapia')}",
            attachment_path=path,
            attachment_filename=f"tratamiento_{treatment_id}.pdf",
        )
    except Exception as e:
        logging.error(f"Error enviando email: {e}")
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")
    finally:
        _cleanup(path)

    return {"message": f"Email enviado a {to_email}"}


# --- Consent PDF ---

@router.get("/consent/{patient_id}/pdf")
def download_consent_pdf(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    data = {
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "patient_dni": patient.dni or "",
        "consent_date": patient.consent_date.strftime("%d-%m-%Y") if patient.consent_date else datetime.now().strftime("%d-%m-%Y"),
    }
    path = generate_consent_pdf(data)
    return FileResponse(path, filename=f"consentimiento_{patient_id}.pdf", media_type="application/pdf")


@router.post("/consent/{patient_id}/email")
def email_consent(
    patient_id: int,
    body: EmailRequest = EmailRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    to_email = body.email or patient.email
    if not to_email:
        raise HTTPException(status_code=400, detail="El paciente no tiene email registrado")

    data = {
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "patient_dni": patient.dni or "",
        "consent_date": patient.consent_date.strftime("%d-%m-%Y") if patient.consent_date else datetime.now().strftime("%d-%m-%Y"),
    }
    path = generate_consent_pdf(data)

    try:
        send_email_with_attachment(
            to_email=to_email,
            subject=f"Consentimiento informado - {os.getenv('CLINIC_NAME', 'Santé')}",
            body=f"Adjunto encontrará el documento de consentimiento informado.\n\nUn saludo,\n{os.getenv('CLINIC_NAME', 'Santé Fisioterapia')}",
            attachment_path=path,
            attachment_filename=f"consentimiento_{patient_id}.pdf",
        )
    except Exception as e:
        logging.error(f"Error enviando email: {e}")
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")
    finally:
        _cleanup(path)

    return {"message": f"Email enviado a {to_email}"}


# --- Data protection consent (static PDF) ---

DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'docs')


class ConsentSignRequest(BaseModel):
    nombre_tutor: str | None = None
    relacion_tutor: str | None = None
    dni_tutor: str | None = None
    fisio_firma: str | None = None
    dni_fisio_firma: str | None = None
    ud_fisioterapia: str | None = None
    observaciones: str | None = None
    patologia_paciente: str | None = None
    dni_paciente: str | None = None
    # Revocación: si es True, se genera un documento de revocación en vez de una firma.
    is_revocacion: bool = False
    nombre_revocante: str | None = None
    observaciones_revoc: str | None = None
    # Firmas manuscritas (PNG en dataURL/base64). La del paciente es obligatoria al
    # firmar; la del tutor solo si se rellenan datos de tutor.
    firma_paciente: str | None = None
    firma_tutor: str | None = None


@router.get("/consent-templates")
def list_consent_templates(
    patient_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las plantillas de consentimiento disponibles (.docx). Ya no se
    excluye ninguna: un paciente puede tener varios documentos del mismo tipo."""
    templates = [f for f in os.listdir(DOCS_PATH) if f.endswith('.docx') and not f.startswith('~$')]
    return [{"filename": f, "name": f.replace('.docx', '')} for f in sorted(templates)]


@router.get("/consent-template-pdf/{template_name}")
def view_template_pdf(
    template_name: str,
    current_user: User = Depends(get_current_user),
):
    """Sirve el PDF en blanco pre-generado de una plantilla."""
    from app.consent_generator import get_blank_pdf_path
    pdf_path = get_blank_pdf_path(template_name)
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF de plantilla no encontrado. Reinicie la aplicación para generarlo.")
    return FileResponse(pdf_path, media_type="application/pdf")


@router.post("/consent-sign/{patient_id}")
def sign_consent(
    patient_id: int,
    template: str,
    data: ConsentSignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera un documento de consentimiento (o su revocación) a partir de una
    plantilla y lo guarda como un DOCUMENTO más del paciente (patient_documents).

    Ya no hay estado 'firmado/revocado': cada generación crea un documento
    independiente que aparece en la lista unificada de documentos del paciente.
    """
    from app.consent_generator import generate_signed_consent
    from app.storage import get_patient_docs_path

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    now = datetime.now(timezone.utc) + timedelta(hours=2)
    nombre_paciente = f"{patient.first_name} {patient.last_name}"
    base_label = template.replace('.docx', '')

    if data.is_revocacion:
        # Documento de revocación: campos de revocación rellenos, originales vacíos.
        template_data = {
            "nombre_paciente": nombre_paciente,
            "dni_paciente": data.dni_paciente or patient.dni or "",
            "nombre_tutor": "", "relacion_tutor": "", "dni_tutor": "",
            "fisio_firma": "", "dni_fisio_firma": "", "ud_fisioterapia": "",
            "patología_paciente": "",
            "nombre_tutor_revoc": data.nombre_revocante or nombre_paciente,
            "nombre_paciente_revoc": nombre_paciente,
            "observaciones_revoc": data.observaciones_revoc or "",
            "dia_revoc": str(now.day),
            "mes_revoc": MESES[now.month],
            "ano_revoc": str(now.year),
            "_suffix": "_revocacion",
        }
        display_name = f"Revocación - {base_label} - {nombre_paciente}.pdf"
    else:
        # Validación de firmas: la del paciente siempre; la del tutor si hay tutor.
        has_tutor = bool(data.nombre_tutor and data.nombre_tutor.strip())
        if not data.firma_paciente:
            raise HTTPException(status_code=400, detail="Falta la firma del paciente.")
        if has_tutor and not data.firma_tutor:
            raise HTTPException(status_code=400, detail="Falta la firma del tutor/representante.")

        template_data = {
            "nombre_paciente": nombre_paciente,
            "dni_paciente": data.dni_paciente or patient.dni or "",
            "nombre_tutor": data.nombre_tutor or "",
            "relacion_tutor": data.relacion_tutor or "",
            "dni_tutor": data.dni_tutor or "",
            "fisio_firma": data.fisio_firma or "",
            "dni_fisio_firma": data.dni_fisio_firma or "",
            "ud_fisioterapia": data.ud_fisioterapia or "",
            "observaciones": data.observaciones or "",
            "patología_paciente": data.patologia_paciente or "",
            # Firmas manuscritas (imágenes). La del tutor solo si hay tutor.
            "firma_paciente": data.firma_paciente,
            "firma_tutor": data.firma_tutor if has_tutor else None,
        }
        display_name = f"{base_label} - {nombre_paciente}.pdf"

    # Generar el PDF en la carpeta unificada de documentos del paciente.
    output_dir = get_patient_docs_path(db)  # exige USB montado (lanza 503 si no)
    try:
        _, pdf_rel = generate_signed_consent(template, template_data, output_dir)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    except Exception as e:
        logging.error(f"Error generando documento: {e}")
        raise HTTPException(status_code=500, detail=f"Error al generar documento: {str(e)}")

    # Registrar como documento del paciente (nombre mostrado = display_name).
    doc = PatientDocument(
        patient_id=patient_id,
        filename=display_name,
        filepath=pdf_rel,  # nombre único en disco (relativo a patient_docs)
        description=None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"id": doc.id, "filename": display_name, "message": "Documento generado"}


# --- Attendance certificate ---

@router.get("/attendance/{patient_id}/pdf")
def download_attendance_pdf(
    patient_id: int,
    date: str | None = None,
    time: str | None = None,
    duration: int | None = None,
    physio_name: str | None = None,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    from app.auth import verify_token
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Token inválido")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    data = {
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "patient_dni": patient.dni or "",
        "date": date or datetime.now().strftime("%d-%m-%Y"),
        "time": time or "",
        "duration": duration,
        "physio_name": physio_name or "",
    }
    path = generate_attendance_pdf(data)
    return FileResponse(path, filename=f"justificante_asistencia_{patient_id}.pdf", media_type="application/pdf")


@router.post("/attendance/{patient_id}/email")
def email_attendance(
    patient_id: int,
    body: EmailRequest = EmailRequest(),
    date: str | None = None,
    time: str | None = None,
    duration: int | None = None,
    physio_name: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    to_email = body.email or patient.email
    if not to_email:
        raise HTTPException(status_code=400, detail="El paciente no tiene email registrado")

    data = {
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "patient_dni": patient.dni or "",
        "date": date or datetime.now().strftime("%d-%m-%Y"),
        "time": time or "",
        "duration": duration,
        "physio_name": physio_name or "",
    }
    path = generate_attendance_pdf(data)

    try:
        send_email_with_attachment(
            to_email=to_email,
            subject=f"Justificante de asistencia - {os.getenv('CLINIC_NAME', 'Santé')}",
            body=f"Adjunto encontrará su justificante de asistencia.\n\nUn saludo,\n{os.getenv('CLINIC_NAME', 'Santé Fisioterapia')}",
            attachment_path=path,
            attachment_filename=f"justificante_asistencia_{patient_id}.pdf",
        )
    except Exception as e:
        logging.error(f"Error enviando email: {e}")
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")
    finally:
        _cleanup(path)

    return {"message": f"Email enviado a {to_email}"}


def _cleanup(path: str):
    try:
        os.unlink(path)
    except OSError:
        pass
