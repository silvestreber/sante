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
from app.db.models import Invoice, Patient, SignedConsent, Treatment, User
from app.email_service import send_email_with_attachment
from app.storage import abs_path, get_signed_docs_path


def _consent_abs_path(db: Session, relative_name: str | None) -> str | None:
    """Reconstruye la ruta absoluta de un PDF de consentimiento a partir del
    nombre relativo guardado en BD y la carpeta base configurada."""
    if not relative_name:
        return None
    # Compatibilidad: si en BD hubiera una ruta absoluta antigua, respetarla.
    if os.path.isabs(relative_name):
        return relative_name
    return abs_path(get_signed_docs_path(db, ensure=False, check_mount=False), relative_name)
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


class ConsentRevokeRequest(BaseModel):
    nombre_revocante: str
    observaciones_revoc: str | None = None


@router.get("/consent-templates")
def list_consent_templates(
    patient_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las plantillas de consentimiento disponibles (.docx), excluyendo las ya firmadas del desplegable."""
    templates = [f for f in os.listdir(DOCS_PATH) if f.endswith('.docx') and not f.startswith('~$')]
    if patient_id:
        signed = db.query(SignedConsent.template_name).filter(
            SignedConsent.patient_id == patient_id,
            SignedConsent.is_revoked == False,
        ).all()
        signed_names = {s[0] for s in signed}
        templates = [f for f in templates if f not in signed_names]
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


@router.get("/all-consents/{patient_id}")
def list_all_consents(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todas las plantillas con su estado de firma para un paciente."""
    templates = [f for f in os.listdir(DOCS_PATH) if f.endswith('.docx') and not f.startswith('~$')]
    signed = db.query(SignedConsent).filter(
        SignedConsent.patient_id == patient_id,
    ).all()
    # Mapear: prioridad vigente > revocado
    signed_map = {}
    for c in signed:
        existing = signed_map.get(c.template_name)
        if not existing or (not c.is_revoked and existing.is_revoked):
            signed_map[c.template_name] = c

    result = []
    for f in sorted(templates):
        consent = signed_map.get(f)
        if consent and not consent.is_revoked:
            result.append({
                "template_name": f.replace('.docx', ''),
                "filename": f,
                "status": "signed",
                "id": consent.id,
                "signed_at": consent.signed_at.isoformat() if consent.signed_at else None,
                "revoked_at": None,
            })
        elif consent and consent.is_revoked:
            result.append({
                "template_name": f.replace('.docx', ''),
                "filename": f,
                "status": "revoked",
                "id": consent.id,
                "signed_at": None,
                "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
            })
        else:
            result.append({
                "template_name": f.replace('.docx', ''),
                "filename": f,
                "status": "unsigned",
                "id": None,
                "signed_at": None,
                "revoked_at": None,
            })
    return result


@router.post("/consent-sign/{patient_id}")
def sign_consent(
    patient_id: int,
    template: str,
    data: ConsentSignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera un consentimiento firmado con los datos del paciente."""
    from app.consent_generator import generate_signed_consent

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Comprobar si ya tiene este consentimiento firmado (no revocado)
    existing = db.query(SignedConsent).filter(
        SignedConsent.patient_id == patient_id,
        SignedConsent.template_name == template,
        SignedConsent.is_revoked == False,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Este consentimiento ya está firmado. Para modificarlo, revóquelo primero.")

    # Si hay uno revocado, eliminar registro y PDFs
    revoked = db.query(SignedConsent).filter(
        SignedConsent.patient_id == patient_id,
        SignedConsent.template_name == template,
        SignedConsent.is_revoked == True,
    ).all()
    for r in revoked:
        for rel in [r.pdf_path, r.revocation_pdf_path]:
            path = _consent_abs_path(db, rel)
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        db.delete(r)
    if revoked:
        db.flush()

    template_data = {
        "nombre_paciente": f"{patient.first_name} {patient.last_name}",
        "dni_paciente": data.dni_paciente or patient.dni or "",
        "nombre_tutor": data.nombre_tutor or "",
        "relacion_tutor": data.relacion_tutor or "",
        "dni_tutor": data.dni_tutor or "",
        "fisio_firma": data.fisio_firma or "",
        "dni_fisio_firma": data.dni_fisio_firma or "",
        "ud_fisioterapia": data.ud_fisioterapia or "",
        "observaciones": data.observaciones or "",
        "patología_paciente": data.patologia_paciente or "",
    }

    output_dir = get_signed_docs_path(db)
    try:
        _, pdf_rel = generate_signed_consent(template, template_data, output_dir)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    except Exception as e:
        logging.error(f"Error generando consentimiento: {e}")
        raise HTTPException(status_code=500, detail=f"Error al generar documento: {str(e)}")

    now_spain = datetime.now(timezone.utc) + timedelta(hours=2)
    consent = SignedConsent(
        patient_id=patient_id,
        template_name=template,
        pdf_path=pdf_rel,
        signed_by=current_user.id,
        signed_at=now_spain,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)

    return {"id": consent.id, "pdf_path": pdf_rel, "message": "Consentimiento firmado"}


@router.post("/consent-revoke/{patient_id}/{consent_id}")
def revoke_consent(
    patient_id: int,
    consent_id: int,
    data: ConsentRevokeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoca un consentimiento firmado generando un nuevo documento con los datos de revocación."""
    from app.consent_generator import generate_signed_consent

    consent = db.query(SignedConsent).filter(
        SignedConsent.id == consent_id,
        SignedConsent.patient_id == patient_id,
        SignedConsent.is_revoked == False,
    ).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado o ya revocado")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    now = datetime.now(timezone.utc) + timedelta(hours=2)

    # Fecha de firma original del consentimiento
    signed_date = consent.signed_at + timedelta(hours=2) if consent.signed_at else now

    template_data = {
        "nombre_paciente": f"{patient.first_name} {patient.last_name}",
        "dni_paciente": patient.dni or "",
        "nombre_tutor": "",
        "relacion_tutor": "",
        "dni_tutor": "",
        "fisio_firma": "",
        "dni_fisio_firma": "",
        "ud_fisioterapia": "",
        "patología_paciente": "",
        # Campos de revocación
        "nombre_tutor_revoc": data.nombre_revocante,
        "nombre_paciente_revoc": f"{patient.first_name} {patient.last_name}",
        "dia_firma_original": str(signed_date.day),
        "mes_num_firma_original": str(signed_date.month).zfill(2),
        "ano_firma_original": str(signed_date.year),
        "observaciones_revoc": data.observaciones_revoc or "",
        "dia_revoc": str(now.day),
        "mes_revoc": MESES[now.month],
        "ano_revoc": str(now.year),
        "_suffix": "_revocacion",
    }

    output_dir = get_signed_docs_path(db)
    try:
        _, pdf_rel = generate_signed_consent(consent.template_name, template_data, output_dir)
    except Exception as e:
        logging.error(f"Error generando revocación: {e}")
        raise HTTPException(status_code=500, detail=f"Error al generar documento: {str(e)}")

    # Marcar el original como revocado
    consent.is_revoked = True
    consent.revoked_at = now
    consent.revocation_pdf_path = pdf_rel
    db.commit()

    return {"message": "Consentimiento revocado", "pdf_path": pdf_rel}


@router.get("/signed-consents/{patient_id}")
def list_signed_consents(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista los consentimientos firmados de un paciente."""
    consents = db.query(SignedConsent).filter(
        SignedConsent.patient_id == patient_id
    ).order_by(SignedConsent.signed_at.desc()).all()
    return [
        {
            "id": c.id,
            "template_name": c.template_name.replace('.docx', ''),
            "signed_at": c.signed_at.isoformat() if c.signed_at else None,
            "pdf_path": c.pdf_path,
            "is_revoked": c.is_revoked,
            "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
            "revocation_pdf_path": c.revocation_pdf_path,
        }
        for c in consents
    ]


@router.get("/signed-consents/{patient_id}/{consent_id}/pdf")
def view_signed_consent_pdf(
    patient_id: int,
    consent_id: int,
    type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    consent = db.query(SignedConsent).filter(
        SignedConsent.id == consent_id,
        SignedConsent.patient_id == patient_id,
    ).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    rel = consent.revocation_pdf_path if type == "revocation" else consent.pdf_path
    pdf_path = _consent_abs_path(db, rel)
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF no encontrado")
    return FileResponse(pdf_path, media_type="application/pdf")


@router.post("/signed-consents/{patient_id}/{consent_id}/email")
def email_signed_consent(
    patient_id: int,
    consent_id: int,
    body: EmailRequest = EmailRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    consent = db.query(SignedConsent).filter(
        SignedConsent.id == consent_id,
        SignedConsent.patient_id == patient_id,
    ).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    to_email = body.email or (patient.email if patient else None)
    if not to_email:
        raise HTTPException(status_code=400, detail="El paciente no tiene email registrado")

    consent_pdf_path = _consent_abs_path(db, consent.pdf_path)
    if not consent_pdf_path or not os.path.exists(consent_pdf_path):
        raise HTTPException(status_code=404, detail="PDF no encontrado")

    try:
        send_email_with_attachment(
            to_email=to_email,
            subject=f"Consentimiento informado - {os.getenv('CLINIC_NAME', 'Santé')}",
            body=f"Adjunto encontrará su consentimiento informado firmado.\n\nUn saludo,\n{os.getenv('CLINIC_NAME', 'Santé Fisioterapia')}",
            attachment_path=consent_pdf_path,
            attachment_filename=os.path.basename(consent_pdf_path),
        )
    except Exception as e:
        logging.error(f"Error enviando email: {e}")
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")

    return {"message": f"Email enviado a {to_email}"}


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
