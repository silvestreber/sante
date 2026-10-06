"""Punto de entrada principal de la aplicación Santé.

Santé es un sistema de gestión para clínicas de fisioterapia. Este módulo
configura y arranca la aplicación FastAPI, registra todos los routers de la API,
monta los ficheros estáticos y define los manejadores globales de errores.

Flujo de arranque (lifespan):
    1. init_db()                  -> crea/migra las tablas de la BD SQLite.
    2. start_reminder_scheduler() -> lanza el hilo daemon de recordatorios de citas.
    3. _generate_blank_pdfs_bg()  -> genera en segundo plano los PDFs en blanco de
                                     las plantillas de consentimiento (puede tardar
                                     >1 min en Raspberry Pi con LibreOffice).

Routers registrados (prefijo /api/...):
    auth          -> login, refresh de token, verificación de contraseña.
    pages         -> vistas HTML (Jinja2) del frontend.
    patients      -> CRUD de pacientes, documentos y búsqueda.
    appointments  -> CRUD de citas, recurrencias y validación de horario.
    clinical      -> historial clínico y sesiones.
    treatments    -> planes de tratamiento/ejercicios.
    billing       -> facturas, bonos de sesiones y exportación Excel.
    documents     -> generación y envío por email de PDFs.
    finance       -> contabilidad manual (ingresos/gastos).
    users         -> gestión de usuarios (solo ADMIN).
    notifications -> avisos internos entre usuarios + WebSocket en tiempo real.
    audit         -> registro de auditoría de acciones.
    config        -> configuración de horarios, festivos y rutas de almacenamiento.
    waitlist      -> lista de espera de pacientes.
    backup        -> exportación e importación de la base de datos.

Manejadores de error globales:
    StorageUnavailableError -> HTTP 503: el USB no está montado.
    Exception               -> HTTP 500: error interno genérico (se loguea en errors.log).

Variables de entorno relevantes:
    LOG_PATH -> ruta del fichero de log (por defecto app/logs/errors.log).
"""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.db.init_db import init_db
from app.routers import auth, pages, patients, appointments, clinical, treatments, billing, documents, finance, users, notifications, audit, config, waitlist, backup
from app.reminders import start_reminder_scheduler

# Los logs se quedan SIEMPRE en la SD (junto al proyecto), no en el USB.
# Default relativo al proyecto para que funcione en cualquier SO.
_DEFAULT_LOG = os.path.join(os.path.dirname(__file__), "logs", "errors.log")
LOG_PATH = os.getenv("LOG_PATH", _DEFAULT_LOG)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def _generate_blank_pdfs_bg():
    """Genera los PDFs en blanco de las plantillas. Se ejecuta en segundo plano
    para NO bloquear el arranque de la app (LibreOffice puede tardar >1 min en la
    Raspberry la primera vez). Los que ya existen se saltan."""
    try:
        from app.consent_generator import generate_blank_pdfs
        generate_blank_pdfs()
        logging.info("PDFs en blanco de consentimientos generados.")
    except Exception as e:
        logging.error(f"Error generando PDFs en blanco: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación (arranque y apagado).

    Inicializa la BD, arranca el scheduler de recordatorios y lanza la
    generación de PDFs en segundo plano. El `yield` separa el código de
    arranque del de apagado (actualmente vacío).
    """
    init_db()
    start_reminder_scheduler()
    # Generar PDFs en blanco en un hilo aparte: la app responde de inmediato y la
    # generación (lenta con LibreOffice) ocurre por detrás sin bloquear el arranque.
    import threading
    threading.Thread(target=_generate_blank_pdfs_bg, daemon=True).start()
    yield


app = FastAPI(title="Santé", docs_url="/docs", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(clinical.router)
app.include_router(treatments.router)
app.include_router(billing.router)
app.include_router(documents.router)
app.include_router(finance.router)
app.include_router(users.router)
app.include_router(notifications.router)
app.include_router(audit.router)
app.include_router(config.router)
app.include_router(waitlist.router)
app.include_router(backup.router)


from app.storage import StorageUnavailableError


@app.exception_handler(StorageUnavailableError)
async def storage_unavailable_handler(request: Request, exc: StorageUnavailableError):
    """HTTP 503: el USB no está montado.

    Se dispara cuando se intenta guardar un fichero (PDF, documento, backup) y
    el punto de montaje del USB no está activo. Devuelve 503 con mensaje claro.
    Nada se escribe en la SD por error.
    """
    logging.error(f"{request.method} {request.url} - StorageUnavailableError: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": (
            "El almacenamiento externo (USB) no está disponible. No se ha guardado nada. "
            "Comprueba que el USB está conectado y montado, y vuelve a intentarlo."
        )},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """HTTP 500: manejador global de excepciones no controladas.

    Loguea el error completo (con traceback) en errors.log y devuelve una
    respuesta genérica al cliente para no exponer detalles internos.
    """
    logging.error(f"{request.method} {request.url} - {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})
