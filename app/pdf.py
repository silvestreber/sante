import os
import tempfile
from datetime import datetime

from dotenv import load_dotenv
from fpdf import FPDF

load_dotenv()

CLINIC_NAME = os.getenv("CLINIC_NAME", "Santé Fisioterapia")
CLINIC_PHONE = os.getenv("CLINIC_PHONE", "")
CLINIC_ADDRESS = os.getenv("CLINIC_ADDRESS", "")
CLINIC_CIF = os.getenv("CLINIC_CIF", "")


class SantePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, CLINIC_NAME, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.cell(0, 4, f"NIF: {CLINIC_CIF} | Tel: {CLINIC_PHONE}", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, CLINIC_ADDRESS, new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        self.set_draw_color(0, 128, 128)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(128)
        self.cell(0, 10, f"{CLINIC_NAME} - {CLINIC_ADDRESS}", align="C")


def generate_invoice_pdf(invoice_data: dict) -> str:
    """Genera PDF de factura/factura simplificada/justificante. Devuelve ruta temporal."""
    pdf = SantePDF()
    pdf.add_page()

    type_labels = {"INVOICE": "FACTURA", "SIMPLIFIED_INVOICE": "FACTURA SIMPLIFICADA", "RECEIPT": "JUSTIFICANTE DE PAGO"}
    method_labels = {"CASH": "Efectivo", "BIZUM": "Bizum"}

    doc_label = type_labels.get(invoice_data["doc_type"], "DOCUMENTO")

    # Title
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, doc_label, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Invoice info
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"N\u00ba: {invoice_data['invoice_number']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Fecha: {invoice_data.get('date', datetime.now().strftime('%d-%m-%Y'))}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Patient info
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Datos del paciente:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Nombre: {invoice_data.get('patient_name', '')}", new_x="LMARGIN", new_y="NEXT")
    if invoice_data.get("patient_dni"):
        pdf.cell(0, 6, f"DNI: {invoice_data['patient_dni']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Table header
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(120, 8, "Concepto", border=1, fill=True)
    pdf.cell(40, 8, "Importe", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    # Table row
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(120, 8, invoice_data.get("description", ""), border=1)
    pdf.cell(40, 8, f"{invoice_data['amount']:.2f} EUR", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    # Total
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(120, 8, "TOTAL", align="R")
    pdf.cell(40, 8, f"{invoice_data['amount']:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")

    # Payment method
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 9)
    method = invoice_data.get("payment_method")
    if method:
        pdf.cell(0, 6, f"M\u00e9todo de pago: {method_labels.get(method, method)}", new_x="LMARGIN", new_y="NEXT")
    status = "Pagado" if invoice_data.get("is_paid") else "Pendiente de pago"
    pdf.cell(0, 6, f"Estado: {status}", new_x="LMARGIN", new_y="NEXT")

    path = tempfile.mktemp(suffix=".pdf", prefix=f"invoice_{invoice_data['invoice_number']}_")
    pdf.output(path)
    return path


def generate_consent_pdf(patient_data: dict) -> str:
    """Genera PDF de consentimiento informado."""
    pdf = SantePDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "CONSENTIMIENTO INFORMADO", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    text = (
        f"D./D\u00f1a. {patient_data.get('patient_name', '')}, "
        f"con DNI {patient_data.get('patient_dni', '___________')}, "
        f"declara haber sido informado/a de los procedimientos de fisioterapia "
        f"que se le van a realizar en {CLINIC_NAME}, habiendo comprendido la "
        f"naturaleza y prop\u00f3sito del tratamiento, los riesgos y beneficios, "
        f"y las alternativas disponibles."
    )
    pdf.multi_cell(0, 6, text)
    pdf.ln(4)

    pdf.multi_cell(0, 6,
        "Asimismo, autoriza al profesional a realizar las t\u00e9cnicas de fisioterapia "
        "que considere necesarias para mi tratamiento, y declaro que he facilitado "
        "de forma veraz mis datos de salud relevantes."
    )
    pdf.ln(4)

    pdf.multi_cell(0, 6,
        "Este consentimiento puede ser revocado en cualquier momento, "
        "sin necesidad de justificaci\u00f3n y sin que ello suponga perjuicio alguno."
    )
    pdf.ln(8)

    date_str = patient_data.get("consent_date", datetime.now().strftime("%d-%m-%Y"))
    pdf.cell(0, 6, f"Fecha: {date_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    pdf.cell(90, 6, "Firma del paciente:", align="L")
    pdf.cell(90, 6, "Firma del profesional:", align="L", new_x="LMARGIN", new_y="NEXT")

    path = tempfile.mktemp(suffix=".pdf", prefix="consent_")
    pdf.output(path)
    return path


def generate_treatment_pdf(treatment_data: dict) -> str:
    """Genera PDF de tratamiento/ejercicios."""
    pdf = SantePDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "TRATAMIENTO / EJERCICIOS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Paciente: {treatment_data.get('patient_name', '')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Fisioterapeuta: {treatment_data.get('physio_name', '')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Fecha: {treatment_data.get('date', datetime.now().strftime('%d-%m-%Y'))}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, treatment_data.get("title", ""), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, treatment_data.get("description", ""))

    path = tempfile.mktemp(suffix=".pdf", prefix="treatment_")
    pdf.output(path)
    return path


def generate_attendance_pdf(attendance_data: dict) -> str:
    """Genera PDF de justificante de asistencia."""
    pdf = SantePDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "JUSTIFICANTE DE ASISTENCIA", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    dni_text = attendance_data.get('patient_dni') or '___________________________'

    pdf.set_font("Helvetica", "", 10)
    text = (
        f"Se certifica que D./D\u00f1a. {attendance_data.get('patient_name', '')}, "
        f"con DNI {dni_text}, "
        f"ha asistido a consulta de fisioterapia en {CLINIC_NAME} "
        f"el d\u00eda {attendance_data.get('date', datetime.now().strftime('%d-%m-%Y'))} "
        f"a las {attendance_data.get('time', '')}."
    )
    pdf.multi_cell(0, 6, text)
    pdf.ln(4)

    if attendance_data.get("duration"):
        pdf.cell(0, 6, f"Duraci\u00f3n de la sesi\u00f3n: {attendance_data['duration']} minutos.", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.cell(0, 6, f"Y para que conste, se expide el presente justificante.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    now = datetime.now()
    fecha_larga = f"{now.day} de {meses[now.month - 1]} de {now.year}"
    pdf.cell(0, 6, f"En {CLINIC_ADDRESS.split(',')[-1].strip() if ',' in CLINIC_ADDRESS else ''}, a {fecha_larga}.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    physio_name = attendance_data.get('physio_name', '')
    if physio_name:
        pdf.cell(0, 6, f"Fdo.: {physio_name}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 6, "Fdo.: El/La fisioterapeuta", new_x="LMARGIN", new_y="NEXT")

    path = tempfile.mktemp(suffix=".pdf", prefix="attendance_")
    pdf.output(path)
    return path
