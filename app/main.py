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

LOG_PATH = os.getenv("LOG_PATH", "C:/PoC/sante/app/logs/errors.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_reminder_scheduler()
    # Generar PDFs en blanco de plantillas de consentimiento
    try:
        from app.consent_generator import generate_blank_pdfs
        generate_blank_pdfs()
    except Exception as e:
        logging.error(f"Error generando PDFs en blanco: {e}")
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"{request.method} {request.url} - {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})
