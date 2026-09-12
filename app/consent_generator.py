"""Genera documentos de consentimiento rellenando plantillas .docx con datos del paciente."""
import base64
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from docx import Document
from docx.shared import Cm

from app.storage import unique_name

# Ancho fijo de la firma en el documento (cm). La firma se escala SIEMPRE a este
# ancho, independientemente del tamaño con que se dibuje en el canvas.
SIGNATURE_WIDTH_CM = 5.0

TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), 'static', 'docs')
BLANK_PDFS_PATH = os.path.join(os.path.dirname(__file__), 'static', 'docs', 'blank_pdfs')

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
    # Marcadores de firma manuscrita: en el PDF en blanco quedan vacíos (sin firma).
    "firma_paciente": "",
    "firma_tutor": "",
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


def _decode_signature(data_url: str) -> io.BytesIO | None:
    """Decodifica una firma en formato dataURL/base64 a un stream PNG listo para insertar.

    Acepta tanto 'data:image/png;base64,XXXX' como el base64 pelado. Devuelve
    None si la entrada está vacía o no es válida.

    IMPORTANTE: el canvas exporta la firma con fondo TRANSPARENTE (RGBA). LibreOffice
    headless renderiza mal la transparencia al convertir a PDF (la firma desaparece).
    Por eso aplanamos la imagen sobre fondo BLANCO opaco, así el PDF la muestra bien."""
    if not data_url:
        return None
    try:
        b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
        raw = base64.b64decode(b64)
        if not raw:
            return None
    except Exception:
        return None

    # Aplanar sobre fondo blanco (elimina el canal alfa que LibreOffice no renderiza bien).
    try:
        from PIL import Image
        src = Image.open(io.BytesIO(raw))
        if src.mode in ("RGBA", "LA") or (src.mode == "P" and "transparency" in src.info):
            src = src.convert("RGBA")
            bg = Image.new("RGB", src.size, (255, 255, 255))
            bg.paste(src, mask=src.split()[-1])  # usar el canal alfa como máscara
            flat = bg
        else:
            flat = src.convert("RGB")
        out = io.BytesIO()
        flat.save(out, format="PNG")
        out.seek(0)
        return out
    except Exception:
        # Si PIL no está disponible o falla, devolver el PNG original tal cual.
        return io.BytesIO(raw)


def _insert_signature_in_paragraph(paragraph, marker: str, image_stream: io.BytesIO) -> bool:
    """Si `paragraph` contiene el marcador, lo sustituye por la imagen a ancho fijo.

    Inserta la imagen EN el run que contiene el marcador (no en un run nuevo al
    final), lo que garantiza que el <w:drawing> quede correctamente enlazado en el
    XML. Soporta que el párrafo tenga varios marcadores en runs distintos (p.ej.
    firma_paciente y firma_tutor en el mismo párrafo)."""
    runs = paragraph.runs
    if not runs:
        return False

    # Caso 1: el marcador está completo dentro de un único run.
    for run in runs:
        if marker in run.text:
            before, _, after = run.text.partition(marker)
            run.text = before  # texto anterior al marcador queda en el run
            image_stream.seek(0)
            run.add_picture(image_stream, width=Cm(SIGNATURE_WIDTH_CM))
            # El texto posterior (p.ej. tabulaciones, otro marcador) va a un run nuevo
            # para no perderlo. Se procesará aparte si contiene otro marcador.
            if after:
                paragraph.add_run(after)
            return True

    # Caso 2: el marcador está partido entre varios runs. Consolidar en el primero.
    full_text = "".join(r.text for r in runs)
    if marker not in full_text:
        return False
    idx = full_text.index(marker)
    before = full_text[:idx]
    after = full_text[idx + len(marker):]
    first = runs[0]
    first.text = before
    for r in runs[1:]:
        r.text = ""
    image_stream.seek(0)
    first.add_picture(image_stream, width=Cm(SIGNATURE_WIDTH_CM))
    if after:
        paragraph.add_run(after)
    return True


def _stamp_signature(doc, marker: str, image_stream: io.BytesIO) -> None:
    """Busca el marcador en todo el documento (cuerpo y tablas) y estampa la firma.
    Si la firma no viene (image_stream None), simplemente elimina el marcador."""
    def _clear_marker_text(paragraph):
        _replace_in_paragraph(paragraph, {marker.strip("{}"): ""})

    if image_stream is None:
        # Sin firma: limpiar el marcador dejándolo vacío.
        for p in doc.paragraphs:
            _clear_marker_text(p)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        _clear_marker_text(p)
        return

    # Con firma: insertar la imagen en el primer párrafo que tenga el marcador.
    for p in doc.paragraphs:
        if _insert_signature_in_paragraph(p, marker, image_stream):
            return
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if _insert_signature_in_paragraph(p, marker, image_stream):
                        return


def fill_consent_template(template_filename: str, data: dict, output_dir: str) -> str:
    """Rellena una plantilla docx con los datos y devuelve la ruta del docx generado.

    El docx se guarda en `output_dir` con un nombre único global.
    """
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

    # --- Firmas manuscritas (imágenes) ---
    # La firma del paciente es siempre; la del tutor solo si viene (hay datos de tutor).
    # Si un marcador existe pero no hay firma, se limpia (queda vacío).
    _stamp_signature(doc, "{{firma_paciente}}", _decode_signature(data.get("firma_paciente")))
    _stamp_signature(doc, "{{firma_tutor}}", _decode_signature(data.get("firma_tutor")))

    os.makedirs(output_dir, exist_ok=True)
    safe_name = re.sub(r'[^\w\-]', '_', data.get("nombre_paciente", "paciente"))
    base_name = template_filename.replace(".docx", "")
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    suffix = data.get("_suffix", "")
    # Nombre lógico + prefijo único global (para que nunca colisione entre carpetas).
    logical_name = f"{base_name}_{safe_name}_{timestamp}{suffix}"
    output_filename = unique_name(logical_name, ".docx")
    output_path = os.path.join(output_dir, output_filename)
    doc.save(output_path)

    return output_path


def convert_docx_to_pdf(docx_path: str) -> str:
    """Convierte un docx a PDF y devuelve la ruta del PDF.

    Multiplataforma:
    - En Linux (Raspberry Pi): usa LibreOffice headless (`soffice --convert-to pdf`).
    - En Windows (desarrollo): usa docx2pdf (Microsoft Word vía COM).
    """
    if sys.platform.startswith("win"):
        return _convert_docx_to_pdf_windows(docx_path)
    return _convert_docx_to_pdf_libreoffice(docx_path)


def _convert_docx_to_pdf_windows(docx_path: str) -> str:
    """Conversión con Microsoft Word (solo Windows, entorno de desarrollo)."""
    import pythoncom
    pythoncom.CoInitialize()
    try:
        from docx2pdf import convert
        pdf_path = docx_path.replace(".docx", ".pdf")
        convert(docx_path, pdf_path)
        return pdf_path
    finally:
        pythoncom.CoUninitialize()


def _find_soffice() -> str:
    """Localiza el ejecutable de LibreOffice. Lanza si no está instalado."""
    exe = os.getenv("SOFFICE_BIN") or shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        raise RuntimeError(
            "LibreOffice no está instalado (no se encontró 'soffice' ni 'libreoffice'). "
            "Instálalo con: sudo apt install libreoffice --no-install-recommends"
        )
    return exe


def _convert_docx_to_pdf_libreoffice(docx_path: str) -> str:
    """Conversión con LibreOffice headless (Linux/Raspberry Pi).

    LibreOffice escribe el PDF con el mismo nombre base en `--outdir`. Usamos un
    perfil de usuario temporal (`-env:UserInstallation`) para evitar conflictos si
    hay varias conversiones a la vez o si el $HOME del servicio no es estándar.
    """
    exe = _find_soffice()
    out_dir = os.path.dirname(os.path.abspath(docx_path))
    expected_pdf = docx_path[:-len(".docx")] + ".pdf" if docx_path.endswith(".docx") else docx_path + ".pdf"

    with tempfile.TemporaryDirectory(prefix="lo_profile_") as profile_dir:
        cmd = [
            exe,
            f"-env:UserInstallation=file://{profile_dir}",
            "--headless", "--norestore",
            "--convert-to", "pdf",
            "--outdir", out_dir,
            docx_path,
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice tardó demasiado en convertir el documento (timeout 120s).")

    if result.returncode != 0 or not os.path.exists(expected_pdf):
        raise RuntimeError(
            f"LibreOffice no pudo convertir el documento a PDF. "
            f"Código: {result.returncode}. Salida: {result.stdout.strip()} {result.stderr.strip()}"
        )
    return expected_pdf


def generate_signed_consent(template_filename: str, data: dict, output_dir: str) -> tuple[str, str]:
    """Genera el documento firmado completo (PDF) en `output_dir`.

    Devuelve una tupla (ruta_absoluta_pdf, nombre_relativo_pdf). El nombre relativo
    es lo que debe persistirse en la BD; la ruta absoluta se reconstruye luego como
    base_de_la_categoria + nombre_relativo.
    """
    docx_path = fill_consent_template(template_filename, data, output_dir)
    pdf_path = convert_docx_to_pdf(docx_path)
    try:
        os.unlink(docx_path)
    except OSError:
        pass
    return pdf_path, os.path.basename(pdf_path)


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
