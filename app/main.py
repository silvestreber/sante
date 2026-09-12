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
    """El USB no está disponible: no se pudo guardar el fichero. Devolvemos 503
    con un mensaje claro para el usuario (nada se ha escrito en la SD)."""
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
    logging.error(f"{request.method} {request.url} - {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})
