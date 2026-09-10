"""Genera documentos de consentimiento rellenando plantillas .docx con datos del paciente."""
import os
import re
from datetime import datetime, timezone, timedelta
from docx import Document

TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), 'static', 'docs')
BLANK_PDFS_PATH = os.path.join(os.path.dirname(__file__), 'static', 'docs', 'blank_pdfs')
SIGNED_DOCS_PATH = os.getenv("SIGNED_DOCS_PATH", "C:/PoC/documentos_firmados")

# Timezone España (UTC+2 en verano, UTC+1 en invierno)
SPAIN_TZ = timedelta(hours=2)

MESES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

# Guiones bajos proporcionales al tamaño del campo
BLANK_NAME = "_" * 35
BLANK_DNI = "_" * 12
BLANK_DAY = "__"
BLANK_MONTH = "_" * 12
BLANK_YEAR = "____"
BLANK_RELATION = "_" * 20
BLANK_TEXT = "_" * 40

# Reemplazos para plantilla en blanco (todos los campos vacíos con guiones)
BLANK_REPLACEMENTS = {
    "nombre_paciente": BLANK_NAME,
    "dni_paciente": BLANK_DNI,
    "dia_firma": BLANK_DAY,
    "mes_firma": BLANK_MONTH,
    "ano_firma": BLANK_YEAR,
    "fisio_firma": BLANK_NAME,
    "dni_fisio_firma": BLANK_DNI,
    "ud_fisioterapia": BLANK_TEXT,
    "patología_paciente": BLANK_TEXT,
    "nombre_paciente_rep": BLANK_NAME,
    "dni_paciente_rep": BLANK_DNI,
    "nombre_tutor": BLANK_NAME,
    "dni_tutor": BLANK_DNI,
    "relacion_tutor": BLANK_RELATION,
    "dia_firma_rep": BLANK_DAY,
    "mes_firma_rep": BLANK_MONTH,
    "ano_firma_rep": BLANK_YEAR,
    "nombre_tutor_revoc": BLANK_NAME,
    "nombre_paciente_revoc": BLANK_NAME,
    "dia_firma_original": BLANK_DAY,
    "mes_num_firma_original": BLANK_DAY,
    "ano_firma_original": BLANK_YEAR,
    "observaciones_revoc": "",
    "dia_revoc": BLANK_DAY,
    "mes_revoc": BLANK_MONTH,
    "ano_revoc": BLANK_YEAR,
}


def _replace_in_paragraph(paragraph, replacements: dict):
    """Reemplaza marcadores {{key}} en un párrafo, manejando runs divididos."""
    full_text = "".join(run.text for run in paragraph.runs)
    if "{{" not in full_text:
        return

    for key, value in replacements.items():
        full_text = full_text.replace("{{" + key + "}}", value or "")

    # Redistribuir el texto en los runs existentes (mantiene formato)
    if paragraph.runs:
        paragraph.runs[0].text = full_text
        for run in paragraph.runs[1:]:
            run.text = ""


def fill_consent_template(template_filename: str, data: dict) -> str:
    """Rellena una plantilla docx con los datos y devuelve la ruta del docx generado."""
    template_path = os.path.join(TEMPLATES_PATH, template_filename)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Plantilla no encontrada: {template_filename}")

    doc = Document(template_path)

    now = datetime.now(timezone.utc) + SPAIN_TZ
    has_tutor = bool(data.get("nombre_tutor"))
    replacements = {
        # --- Firma principal (todos los documentos) ---
        "nombre_paciente": data.get("nombre_paciente", ""),
        "dni_paciente": data.get("dni_paciente", ""),
        "dia_firma": str(now.day),
        "mes_firma": MESES[now.month],
        "ano_firma": str(now.year),
        # --- Campos específicos CI FISIOTERAPIA GENERAL ---
        "fisio_firma": data.get("fisio_firma", ""),
        "dni_fisio_firma": data.get("dni_fisio_firma", ""),
        "ud_fisioterapia": data.get("ud_fisioterapia", ""),
        # --- Campo específico CI PUNCION SECA ---
        "patología_paciente": data.get("patología_paciente", ""),
        # --- Autorización tutor/representante ---
        "nombre_paciente_rep": data.get("nombre_paciente", "") if has_tutor else BLANK_NAME,
        "dni_paciente_rep": data.get("dni_paciente", "") if has_tutor else BLANK_DNI,
        "nombre_tutor": data.get("nombre_tutor", "") if has_tutor else BLANK_NAME,
        "dni_tutor": data.get("dni_tutor", "") if has_tutor else BLANK_DNI,
        "relacion_tutor": data.get("relacion_tutor", "") if has_tutor else BLANK_RELATION,
        "dia_firma_rep": str(now.day) if has_tutor else BLANK_DAY,
        "mes_firma_rep": MESES[now.month] if has_tutor else BLANK_MONTH,
        "ano_firma_rep": str(now.year) if has_tutor else BLANK_YEAR,
        # --- Revocación ---
        "nombre_tutor_revoc": data.get("nombre_tutor_revoc", "") or BLANK_NAME,
        "nombre_paciente_revoc": data.get("nombre_paciente_revoc", "") or BLANK_NAME,
        "dia_firma_original": data.get("dia_firma_original", "") or BLANK_DAY,
        "mes_num_firma_original": data.get("mes_num_firma_original", "") or BLANK_DAY,
        "ano_firma_original": data.get("ano_firma_original", "") or BLANK_YEAR,
        "observaciones_revoc": data.get("observaciones_revoc", ""),
        "dia_revoc": data.get("dia_revoc", "") or BLANK_DAY,
        "mes_revoc": data.get("mes_revoc", "") or BLANK_MONTH,
        "ano_revoc": data.get("ano_revoc", "") or BLANK_YEAR,
    }

    for paragraph in doc.paragraphs:
        _replace_in_paragraph(paragraph, replacements)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_in_paragraph(p, replacements)

    for section in doc.sections:
        for header in [section.header, section.first_page_header]:
            if header:
                for p in header.paragraphs:
                    _replace_in_paragraph(p, replacements)
        for footer in [section.footer, section.first_page_footer]:
            if footer:
                for p in footer.paragraphs:
                    _replace_in_paragraph(p, replacements)

    os.makedirs(SIGNED_DOCS_PATH, exist_ok=True)
    safe_name = re.sub(r'[^\w\-]', '_', data.get("nombre_paciente", "paciente"))
    base_name = template_filename.replace(".docx", "")
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    suffix = data.get("_suffix", "")
    output_filename = f"{base_name}_{safe_name}_{timestamp}{suffix}.docx"
    output_path = os.path.join(SIGNED_DOCS_PATH, output_filename)
    doc.save(output_path)

    return output_path


def convert_docx_to_pdf(docx_path: str) -> str:
    """Convierte un docx a PDF. Devuelve la ruta del PDF."""
    import pythoncom
    pythoncom.CoInitialize()
    try:
        from docx2pdf import convert
        pdf_path = docx_path.replace(".docx", ".pdf")
        convert(docx_path, pdf_path)
        return pdf_path
    finally:
        pythoncom.CoUninitialize()


def generate_signed_consent(template_filename: str, data: dict) -> str:
    """Genera el documento firmado completo (PDF). Devuelve ruta del PDF."""
    docx_path = fill_consent_template(template_filename, data)
    pdf_path = convert_docx_to_pdf(docx_path)
    try:
        os.unlink(docx_path)
    except OSError:
        pass
    return pdf_path


def generate_blank_pdfs():
    """Genera PDFs en blanco de todas las plantillas. Se ejecuta una vez al arrancar."""
    os.makedirs(BLANK_PDFS_PATH, exist_ok=True)
    templates = [f for f in os.listdir(TEMPLATES_PATH) if f.endswith('.docx') and not f.startswith('~$')]
    for template_filename in templates:
        pdf_name = template_filename.replace('.docx', '.pdf')
        pdf_path = os.path.join(BLANK_PDFS_PATH, pdf_name)
        if os.path.exists(pdf_path):
            continue
        template_path = os.path.join(TEMPLATES_PATH, template_filename)
        doc = Document(template_path)
        for paragraph in doc.paragraphs:
            _replace_in_paragraph(paragraph, BLANK_REPLACEMENTS)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        _replace_in_paragraph(p, BLANK_REPLACEMENTS)
        for section in doc.sections:
            for header in [section.header, section.first_page_header]:
                if header:
                    for p in header.paragraphs:
                        _replace_in_paragraph(p, BLANK_REPLACEMENTS)
            for footer in [section.footer, section.first_page_footer]:
                if footer:
                    for p in footer.paragraphs:
                        _replace_in_paragraph(p, BLANK_REPLACEMENTS)
        docx_tmp = os.path.join(BLANK_PDFS_PATH, template_filename)
        doc.save(docx_tmp)
        convert_docx_to_pdf(docx_tmp)
        try:
            os.unlink(docx_tmp)
        except OSError:
            pass


def get_blank_pdf_path(template_filename: str) -> str | None:
    """Devuelve la ruta del PDF en blanco de una plantilla."""
    pdf_name = template_filename.replace('.docx', '.pdf')
    pdf_path = os.path.join(BLANK_PDFS_PATH, pdf_name)
    return pdf_path if os.path.exists(pdf_path) else None
