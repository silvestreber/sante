from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/calendar")


@router.get("/patients", response_class=HTMLResponse)
def patients_page(request: Request):
    return templates.TemplateResponse(request, "patients/list.html")


@router.get("/patients/new", response_class=HTMLResponse)
def patients_new_page(request: Request):
    return templates.TemplateResponse(request, "patients/form.html")


@router.get("/patients/{patient_id}", response_class=HTMLResponse)
def patients_detail_page(request: Request, patient_id: int):
    return templates.TemplateResponse(request, "patients/detail.html")


@router.get("/patients/{patient_id}/edit", response_class=HTMLResponse)
def patients_edit_page(request: Request, patient_id: int):
    return templates.TemplateResponse(request, "patients/form.html")


@router.get("/calendar", response_class=HTMLResponse)
def calendar_page(request: Request):
    return templates.TemplateResponse(request, "appointments/calendar.html")


@router.get("/patients/{patient_id}/clinical", response_class=HTMLResponse)
def clinical_history_page(request: Request, patient_id: int):
    return templates.TemplateResponse(request, "clinical/history.html")


@router.get("/patients/{patient_id}/documents", response_class=HTMLResponse)
def patient_documents_page(request: Request, patient_id: int):
    return templates.TemplateResponse(request, "patients/documents.html")


@router.get("/patients/{patient_id}/packs", response_class=HTMLResponse)
def patient_packs_page(request: Request, patient_id: int):
    return templates.TemplateResponse(request, "patients/packs.html")


@router.get("/patients/{patient_id}/treatments", response_class=HTMLResponse)
def treatments_list_page(request: Request, patient_id: int):
    return templates.TemplateResponse(request, "treatments/list.html")


@router.get("/patients/{patient_id}/treatments/new", response_class=HTMLResponse)
def treatments_new_page(request: Request, patient_id: int):
    return templates.TemplateResponse(request, "treatments/form.html")


@router.get("/patients/{patient_id}/treatments/{treatment_id}/edit", response_class=HTMLResponse)
def treatments_edit_page(request: Request, patient_id: int, treatment_id: int):
    return templates.TemplateResponse(request, "treatments/form.html")


@router.get("/billing", response_class=HTMLResponse)
def billing_page(request: Request):
    return templates.TemplateResponse(request, "billing/list.html")


@router.get("/patients/{patient_id}/billing", response_class=HTMLResponse)
def patient_billing_page(request: Request, patient_id: int):
    return templates.TemplateResponse(request, "billing/patient.html")


@router.get("/finance", response_class=HTMLResponse)
def finance_page(request: Request):
    return templates.TemplateResponse(request, "finance/list.html")


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    return templates.TemplateResponse(request, "users/list.html")


@router.get("/notifications", response_class=HTMLResponse)
def notifications_page(request: Request):
    return templates.TemplateResponse(request, "notifications/list.html")


@router.get("/audit-log", response_class=HTMLResponse)
def audit_log_page(request: Request):
    return templates.TemplateResponse(request, "audit/list.html")


@router.get("/config", response_class=HTMLResponse)
def config_page(request: Request):
    return templates.TemplateResponse(request, "config/schedule.html")


@router.get("/waitlist", response_class=HTMLResponse)
def waitlist_page(request: Request):
    return templates.TemplateResponse(request, "waitlist/list.html")


@router.get("/docs/permisos", response_class=HTMLResponse)
def permisos_page(request: Request):
    return templates.TemplateResponse(request, "docs/permisos.html")


@router.get("/docs/funcionalidades", response_class=HTMLResponse)
def funcionalidades_page(request: Request):
    import markdown
    with open("funcionalidades.md", "r", encoding="utf-8") as f:
        content = f.read()
    html_content = markdown.markdown(content, extensions=["tables", "fenced_code"])
    return templates.TemplateResponse(request, "docs/markdown.html", {"content": html_content})


NOTES_MARKER = "## Notas"
TODO_PATH = "TODO.md"


class NotesBody(BaseModel):
    content: str


@router.get("/api/notes")
def get_notes():
    with open(TODO_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    if NOTES_MARKER in text:
        notes = text.split(NOTES_MARKER, 1)[1].strip()
    else:
        notes = ""
    return {"content": notes}


@router.put("/api/notes")
def save_notes(body: NotesBody):
    with open(TODO_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    if NOTES_MARKER in text:
        before = text.split(NOTES_MARKER, 1)[0]
    else:
        before = text.rstrip() + "\n\n"
    new_content = before + NOTES_MARKER + "\n\n" + body.content.strip() + "\n"
    with open(TODO_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    return {"message": "Notas guardadas"}
