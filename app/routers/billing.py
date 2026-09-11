import glob
import io
import os
from datetime import date, datetime, timezone

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.audit_log import log_action
from app.db.database import get_db
from app.db.models import (
    DocType, EntryType, FinanceEntry, Invoice, Patient, PaymentMethod, SessionPack, User,
)
from app.pdf import generate_invoice_pdf
from app.storage import abs_path, get_invoices_path, unique_name

import shutil

EXCEL_TEMPLATE_GLOB = os.path.join(os.path.dirname(__file__), "..", "..", "Eugenia Facturaci*.xlsx")

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _invoice_pdf_abs(db: Session, invoice: "Invoice") -> str | None:
    """Ruta absoluta del PDF de una factura, o None si no tiene fichero asociado."""
    if not invoice.pdf_filename:
        return None
    if os.path.isabs(invoice.pdf_filename):
        return invoice.pdf_filename  # compatibilidad con datos antiguos
    return abs_path(get_invoices_path(db, ensure=False), invoice.pdf_filename)


def _delete_invoice_pdf(db: Session, invoice: "Invoice") -> None:
    """Borra el PDF de una factura si existe."""
    path = _invoice_pdf_abs(db, invoice)
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def _save_invoice_pdf(db: Session, invoice: "Invoice", pdf_data: dict) -> None:
    """(Re)genera el PDF de una factura con nombre único global y lo guarda en la
    carpeta configurada. Borra el PDF anterior si lo hubiera y actualiza
    invoice.pdf_filename. No hace commit."""
    _delete_invoice_pdf(db, invoice)
    base = get_invoices_path(db)
    tmp_path = generate_invoice_pdf(pdf_data)
    filename = unique_name(invoice.invoice_number, ".pdf")
    final_path = os.path.join(base, filename)
    shutil.move(tmp_path, final_path)
    invoice.pdf_filename = filename


# --- Schemas ---

class InvoiceCreate(BaseModel):
    patient_id: int
    appointment_id: int | None = None
    session_pack_id: int | None = None
    doc_type: DocType
    amount: float
    payment_method: PaymentMethod | None = None
    is_paid: bool = False


class InvoiceUpdate(BaseModel):
    doc_type: DocType | None = None
    amount: float | None = None
    payment_method: PaymentMethod | None = None
    is_paid: bool | None = None
    appointment_id: int | None = None
    session_pack_id: int | None = None
    clear_appointment: bool = False
    clear_session_pack: bool = False


class SessionPackCreate(BaseModel):
    patient_id: int
    total_sessions: int
    price: float
    expires_at: str | None = None


# --- Helpers ---

def _next_invoice_number(db: Session, doc_type: DocType) -> str:
    year = datetime.now().year
    prefix = {"INVOICE": "F", "SIMPLIFIED_INVOICE": "FS", "RECEIPT": "J"}[doc_type.value]
    pattern = f"{prefix}-{year}-%"
    last = (
        db.query(Invoice)
        .filter(Invoice.invoice_number.like(pattern))
        .order_by(Invoice.id.desc())
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.invoice_number.rsplit("-", 1)[1]) + 1
        except (ValueError, IndexError):
            pass
    return f"{prefix}-{year}-{seq:04d}"


def _register_income(db: Session, invoice: Invoice, user_id: int):
    """Registra un ingreso en contabilidad vinculado a la factura.
    No registra si el pago es con bono (session_pack_id sin payment_method),
    ya que el ingreso del bono se registra al crearlo."""
    if invoice.session_pack_id and not invoice.payment_method:
        return
    patient = db.query(Patient).filter(Patient.id == invoice.patient_id).first()
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else ""
    desc = f"{invoice.invoice_number} - {patient_name}"
    entry = FinanceEntry(
        entry_type=EntryType.INCOME,
        amount=invoice.amount,
        description=desc,
        category="Cobro paciente",
        date=invoice.created_at.date() if invoice.created_at else date.today(),
        invoice_id=invoice.id,
        created_by=user_id,
    )
    db.add(entry)
    db.commit()


def _remove_income(db: Session, invoice_id: int):
    """Elimina el ingreso de contabilidad vinculado a una factura."""
    entry = db.query(FinanceEntry).filter(FinanceEntry.invoice_id == invoice_id).first()
    if entry:
        db.delete(entry)
        db.commit()


# --- Invoices ---

@router.get("/invoices/patient/{patient_id}")
def list_invoices(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    invoices = (
        db.query(Invoice)
        .filter(Invoice.patient_id == patient_id)
        .order_by(Invoice.created_at.desc())
        .all()
    )
    return [
        {
            "id": i.id,
            "invoice_number": i.invoice_number,
            "doc_type": i.doc_type.value,
            "amount": i.amount,
            "appointment_id": i.appointment_id,
            "appointment_date": i.appointment.start_time.strftime("%d-%m-%Y %H:%M") if i.appointment else None,
            "session_pack_id": i.session_pack_id,
            "session_pack_label": f"Bono {i.session_pack.total_sessions} sesiones" if i.session_pack else None,
            "payment_method": i.payment_method.value if i.payment_method else None,
            "is_paid": i.is_paid,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in invoices
    ]


@router.post("/invoices", status_code=201)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    invoice = Invoice(
        patient_id=data.patient_id,
        appointment_id=data.appointment_id,
        session_pack_id=data.session_pack_id,
        invoice_number=_next_invoice_number(db, data.doc_type),
        doc_type=data.doc_type,
        amount=data.amount,
        payment_method=data.payment_method,
        is_paid=data.is_paid,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Generar y guardar PDF
    description = ""
    if invoice.appointment:
        description = f"Cita {invoice.appointment.start_time.strftime('%d-%m-%Y %H:%M')}"
    elif invoice.session_pack:
        description = f"Bono {invoice.session_pack.total_sessions} sesiones"

    pdf_data = {
        "invoice_number": invoice.invoice_number,
        "doc_type": invoice.doc_type.value,
        "amount": invoice.amount,
        "description": description,
        "payment_method": invoice.payment_method.value if invoice.payment_method else None,
        "is_paid": invoice.is_paid,
        "date": invoice.created_at.strftime("%d-%m-%Y") if invoice.created_at else None,
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "patient_dni": patient.dni or "",
    }
    _save_invoice_pdf(db, invoice, pdf_data)
    db.commit()

    log_action(db, current_user.id, "CREAR", "FACTURA", invoice.id, f"{invoice.invoice_number}")

    # Registrar ingreso en contabilidad si está pagado
    if invoice.is_paid:
        _register_income(db, invoice, current_user.id)

    return {"id": invoice.id, "invoice_number": invoice.invoice_number, "message": "Documento creado"}


@router.put("/invoices/{invoice_id}")
def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    was_paid = invoice.is_paid

    if data.doc_type is not None:
        invoice.doc_type = data.doc_type
    if data.amount is not None:
        invoice.amount = data.amount
    if data.payment_method is not None:
        invoice.payment_method = data.payment_method
    if data.is_paid is not None:
        invoice.is_paid = data.is_paid
    if data.clear_appointment:
        invoice.appointment_id = None
    elif data.appointment_id is not None:
        invoice.appointment_id = data.appointment_id
    if data.clear_session_pack:
        invoice.session_pack_id = None
    elif data.session_pack_id is not None:
        invoice.session_pack_id = data.session_pack_id

    db.commit()
    db.refresh(invoice)

    # Gestionar ingreso en contabilidad
    if not was_paid and invoice.is_paid:
        _register_income(db, invoice, current_user.id)
    elif was_paid and not invoice.is_paid:
        _remove_income(db, invoice.id)
    elif was_paid and invoice.is_paid:
        # Actualizar importe si cambió
        existing = db.query(FinanceEntry).filter(FinanceEntry.invoice_id == invoice.id).first()
        if existing:
            existing.amount = invoice.amount
            db.commit()

    # Regenerar PDF
    patient = db.query(Patient).filter(Patient.id == invoice.patient_id).first()
    description = ""
    if invoice.appointment:
        description = f"Cita {invoice.appointment.start_time.strftime('%d-%m-%Y %H:%M')}"
    elif invoice.session_pack:
        description = f"Bono {invoice.session_pack.total_sessions} sesiones"

    pdf_data = {
        "invoice_number": invoice.invoice_number,
        "doc_type": invoice.doc_type.value,
        "amount": invoice.amount,
        "description": description,
        "payment_method": invoice.payment_method.value if invoice.payment_method else None,
        "is_paid": invoice.is_paid,
        "date": invoice.created_at.strftime("%d-%m-%Y") if invoice.created_at else None,
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "patient_dni": patient.dni or "",
    }
    _save_invoice_pdf(db, invoice, pdf_data)
    db.commit()

    log_action(db, current_user.id, "EDITAR", "FACTURA", invoice.id, invoice.invoice_number)
    return {"message": "Factura actualizada"}


@router.get("/invoices/{invoice_id}/pdf")
def view_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import FileResponse
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    pdf_path = _invoice_pdf_abs(db, invoice)
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF no encontrado")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{invoice.invoice_number}.pdf", content_disposition_type="inline")


@router.delete("/invoices/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    # Eliminar ingreso asociado si estaba pagado
    if invoice.is_paid:
        _remove_income(db, invoice.id)

    # Si está asociado a una cita o bono, marcar como no pagado (queda pendiente)
    if invoice.appointment_id or invoice.session_pack_id:
        invoice.is_paid = False
        invoice.payment_method = None
        db.commit()

        # Regenerar PDF con estado pendiente
        patient = db.query(Patient).filter(Patient.id == invoice.patient_id).first()
        description = ""
        if invoice.appointment:
            description = f"Cita {invoice.appointment.start_time.strftime('%d-%m-%Y %H:%M')}"
        elif invoice.session_pack:
            description = f"Bono {invoice.session_pack.total_sessions} sesiones"
        pdf_data = {
            "invoice_number": invoice.invoice_number,
            "doc_type": invoice.doc_type.value,
            "amount": invoice.amount,
            "description": description,
            "payment_method": None,
            "is_paid": False,
            "date": invoice.created_at.strftime("%d-%m-%Y") if invoice.created_at else None,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "patient_dni": patient.dni or "",
        }
        _save_invoice_pdf(db, invoice, pdf_data)
        db.commit()

        log_action(db, current_user.id, "REVERTIR_PAGO", "FACTURA", invoice_id, invoice.invoice_number)
        return {"message": "Pago revertido, documento marcado como pendiente"}
    else:
        # Sin asociación: eliminar completamente
        _delete_invoice_pdf(db, invoice)
        invoice_number = invoice.invoice_number
        db.delete(invoice)
        db.commit()
        log_action(db, current_user.id, "ELIMINAR", "FACTURA", invoice_id, invoice_number)
        return {"message": "Documento eliminado"}


@router.get("/pending")
def list_pending_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = (
        db.query(Patient, func.sum(Invoice.amount))
        .join(Invoice, Invoice.patient_id == Patient.id)
        .filter(Invoice.is_paid == False)
        .group_by(Patient.id)
        .all()
    )
    return [
        {
            "patient_id": p.id,
            "patient_name": f"{p.first_name} {p.last_name}",
            "pending_amount": amount,
        }
        for p, amount in results
    ]


# --- Session Packs (Bonos) ---

@router.get("/packs/patient/{patient_id}")
def list_packs(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    packs = (
        db.query(SessionPack)
        .filter(SessionPack.patient_id == patient_id)
        .order_by(SessionPack.created_at.desc())
        .all()
    )
    return [
        {
            "id": sp.id,
            "total_sessions": sp.total_sessions,
            "used_sessions": sp.used_sessions,
            "remaining": sp.total_sessions - sp.used_sessions,
            "price": sp.price,
            "created_at": sp.created_at.isoformat() if sp.created_at else None,
            "expires_at": sp.expires_at.isoformat() if sp.expires_at else None,
            "is_cancelled": sp.is_cancelled,
            "active": not sp.is_cancelled and sp.used_sessions < sp.total_sessions and (not sp.expires_at or sp.expires_at >= date.today()),
            "expired": not sp.is_cancelled and sp.expires_at is not None and sp.expires_at < date.today(),
            "pending_invoice_id": next((i.id for i in db.query(Invoice).filter(Invoice.session_pack_id == sp.id, Invoice.is_paid == False).all()), None),
        }
        for sp in packs
    ]


@router.post("/packs", status_code=201)
def create_pack(
    data: SessionPackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    pack = SessionPack(
        patient_id=data.patient_id,
        total_sessions=data.total_sessions,
        used_sessions=0,
        price=data.price,
        expires_at=date.fromisoformat(data.expires_at) if data.expires_at else None,
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return {"id": pack.id, "message": "Bono creado"}


@router.post("/packs/{pack_id}/consume")
def consume_session(
    pack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = db.query(SessionPack).filter(SessionPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Bono no encontrado")
    if pack.used_sessions >= pack.total_sessions:
        raise HTTPException(status_code=400, detail="Bono agotado")
    if pack.expires_at and date.today() > pack.expires_at:
        raise HTTPException(status_code=400, detail="Bono caducado")
    pack.used_sessions += 1
    db.commit()
    return {"message": "Sesión consumida", "remaining": pack.total_sessions - pack.used_sessions}


@router.put("/packs/{pack_id}")
def update_pack(
    pack_id: int,
    data: SessionPackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = db.query(SessionPack).filter(SessionPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Bono no encontrado")
    pack.total_sessions = data.total_sessions
    pack.price = data.price
    pack.expires_at = date.fromisoformat(data.expires_at) if data.expires_at else None
    db.commit()

    # Actualizar factura, ingreso y regenerar PDF si cambió el precio
    invoice = db.query(Invoice).filter(
        Invoice.session_pack_id == pack_id,
        Invoice.is_paid == True,
        Invoice.payment_method.isnot(None),
    ).first()
    if invoice and invoice.amount != data.price:
        invoice.amount = data.price
        db.commit()
        db.refresh(invoice)

        # Actualizar ingreso en contabilidad
        entry = db.query(FinanceEntry).filter(FinanceEntry.invoice_id == invoice.id).first()
        if entry:
            entry.amount = data.price
            db.commit()

        # Regenerar PDF
        patient = db.query(Patient).filter(Patient.id == invoice.patient_id).first()
        pdf_data = {
            "invoice_number": invoice.invoice_number,
            "doc_type": invoice.doc_type.value,
            "amount": invoice.amount,
            "description": f"Bono {pack.total_sessions} sesiones",
            "payment_method": invoice.payment_method.value if invoice.payment_method else None,
            "is_paid": invoice.is_paid,
            "date": invoice.created_at.strftime("%d-%m-%Y") if invoice.created_at else None,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "patient_dni": patient.dni or "",
        }
        _save_invoice_pdf(db, invoice, pdf_data)
        db.commit()

    return {"message": "Bono actualizado"}


@router.delete("/packs/{pack_id}")
def cancel_pack(
    pack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pack = db.query(SessionPack).filter(SessionPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Bono no encontrado")
    pack.is_cancelled = True
    db.commit()

    # Si el bono estaba pagado, eliminar documento de cobro y revertir contabilidad
    invoice = db.query(Invoice).filter(Invoice.session_pack_id == pack_id).first()
    if invoice and invoice.is_paid:
        # Eliminar ingreso de contabilidad
        _remove_income(db, invoice.id)
        # Eliminar PDF
        _delete_invoice_pdf(db, invoice)
        # Eliminar factura
        invoice_number = invoice.invoice_number
        db.delete(invoice)
        db.commit()
        log_action(db, current_user.id, "ELIMINAR", "FACTURA", invoice.id, f"{invoice_number} (cancelación bono)")
    elif invoice and not invoice.is_paid:
        # Si estaba pendiente de pago, no se hace nada con la factura
        pass

    log_action(db, current_user.id, "CANCELAR", "BONO", pack_id, f"Paciente {pack.patient_id}")
    return {"message": "Bono cancelado"}


# --- Exportar facturación a Excel para gestoría ---

def _find_excel_template() -> str:
    candidates = sorted(
        [f for f in glob.glob(EXCEL_TEMPLATE_GLOB) if "silver" not in f.lower() and "~$" not in f and "vac" not in f.lower()],
        key=lambda f: os.path.getsize(f),
        reverse=True,
    )
    if not candidates:
        raise HTTPException(status_code=500, detail="No se encontró el archivo Excel plantilla en la raíz del proyecto.")
    return candidates[0]


def _payment_method_label(pm) -> str:
    if pm is None:
        return ""
    mapping = {"CASH": "efectivo", "CARD": "tarjeta", "TRANSFER": "transferencia", "INSURANCE": "seguro"}
    return mapping.get(pm.value if hasattr(pm, "value") else str(pm), str(pm).lower())


def _invoice_concept(invoice: Invoice) -> str:
    if invoice.session_pack:
        return f"Bono {invoice.session_pack.total_sessions} sesiones"
    return "Sesión de fisioterapia"


@router.post("/export-excel")
def export_billing_excel(
    date_from: str = Query(..., description="Fecha inicio YYYY-MM-DD"),
    date_to: str = Query(..., description="Fecha fin YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        d_from = date.fromisoformat(date_from)
        d_to = date.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")

    template_path = _find_excel_template()
    wb = openpyxl.load_workbook(template_path)

    # ── CLIENTES ──────────────────────────────────────────────────────────────
    ws_cli = wb["CLIENTES"]

    # Leer IDs ya presentes (columna A, desde fila 2)
    existing_ids: set[int] = set()
    last_data_row = 1
    for i, row in enumerate(ws_cli.iter_rows(min_row=2, min_col=1, max_col=1, values_only=True), start=2):
        if row[0] is not None:
            try:
                existing_ids.add(int(row[0]))
                last_data_row = i
            except (ValueError, TypeError):
                pass

    # Pacientes activos ordenados por id desc (más recientes primero)
    all_patients = (
        db.query(Patient)
        .filter(Patient.is_active == True)
        .order_by(Patient.id.desc())
        .all()
    )

    # Recoger los nuevos hasta encontrar uno ya existente
    new_patients = []
    for p in all_patients:
        if p.id in existing_ids:
            break
        new_patients.append(p)
    new_patients.sort(key=lambda p: p.id)

    next_row = last_data_row + 1
    for p in new_patients:
        ws_cli.cell(row=next_row, column=1, value=p.id)
        ws_cli.cell(row=next_row, column=2, value=f"{p.last_name}, {p.first_name}")
        ws_cli.cell(row=next_row, column=3, value=p.dni or "")
        ws_cli.cell(row=next_row, column=4, value=f"{p.first_name} {p.last_name}")
        ws_cli.cell(row=next_row, column=5, value=p.address or "")
        ws_cli.cell(row=next_row, column=6, value="")
        ws_cli.cell(row=next_row, column=7, value="")
        ws_cli.cell(row=next_row, column=8, value="")
        ws_cli.cell(row=next_row, column=9, value=p.phone or "")
        ws_cli.cell(row=next_row, column=10, value=p.email or "")
        next_row += 1

    # ── FACTURAS ──────────────────────────────────────────────────────────────
    ws_fac = wb["FACTURAS"]

    fac_next_row = 2
    for i, row in enumerate(ws_fac.iter_rows(min_row=2, min_col=1, max_col=1, values_only=True), start=2):
        if row[0] is not None:
            fac_next_row = i + 1

    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.is_paid == True,
            Invoice.created_at >= datetime.combine(d_from, datetime.min.time()),
            Invoice.created_at <= datetime.combine(d_to, datetime.max.time()),
        )
        .order_by(Invoice.created_at.asc())
        .all()
    )

    for inv in invoices:
        r = fac_next_row
        fecha = inv.created_at.date() if inv.created_at else d_from
        physio = db.query(User).filter(User.id == inv.appointment.physio_id).first() if inv.appointment else None
        colaborador = "x" if physio and physio.is_colaborador else ""
        ws_fac.cell(row=r, column=1, value="P")
        ws_fac.cell(row=r, column=3, value=fecha)
        ws_fac.cell(row=r, column=4, value=inv.patient_id)
        ws_fac.cell(row=r, column=5, value=_invoice_concept(inv))
        ws_fac.cell(row=r, column=6, value=inv.amount)
        ws_fac.cell(row=r, column=7, value=_payment_method_label(inv.payment_method))
        ws_fac.cell(row=r, column=8, value=colaborador)
        ws_fac.cell(row=r, column=9,  value=f"=VLOOKUP(D{r},CLIENTES!A:H,2,0)")
        ws_fac.cell(row=r, column=10, value=f"=VLOOKUP(D{r},CLIENTES!A:H,4,0)")
        ws_fac.cell(row=r, column=11, value=f"=VLOOKUP(D{r},CLIENTES!A:H,3,0)")
        ws_fac.cell(row=r, column=12, value=f"=VLOOKUP(D{r},CLIENTES!A:H,5,0)")
        ws_fac.cell(row=r, column=13, value=f"=CONCATENATE(N{r},R{r},O{r})")
        ws_fac.cell(row=r, column=14, value=f"=VLOOKUP(D{r},CLIENTES!A:H,6,0)")
        ws_fac.cell(row=r, column=15, value=f"=VLOOKUP(D{r},CLIENTES!A:H,7,0)")
        ws_fac.cell(row=r, column=16, value=f"=VLOOKUP(D{r},CLIENTES!A:H,8,0)")
        fac_next_row += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Facturacion_{date_from}_{date_to}.xlsx"
    log_action(db, current_user.id, "EXPORTAR", "FACTURACION_EXCEL", 0,
               f"{date_from} a {date_to} ({len(invoices)} facturas, {len(new_patients)} clientes nuevos)")

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
