# Contexto para continuación de desarrollo — Santé

## Proyecto
Aplicación web de gestión de clínica de fisioterapia. Stack: FastAPI + SQLite + Jinja2 + Tailwind CSS + FullCalendar. Se ejecuta en Raspberry Pi (producción) y Windows (desarrollo).

**Ruta del proyecto**: `C:\PoC\sante`

## Estructura principal
```
app/
├── main.py                 # FastAPI app, registro de routers
├── auth.py                 # JWT, bcrypt, roles
├── consent_generator.py    # Genera consentimientos firmados (.docx → PDF)
├── email_service.py        # SMTP envío emails
├── pdf.py                  # Generación PDFs (facturas, justificantes, etc.)
├── websocket_manager.py    # WebSocket notificaciones tiempo real
├── db/
│   ├── database.py         # SQLAlchemy engine (sqlite:///./sante.db)
│   └── models.py           # Todos los modelos
├── routers/
│   ├── appointments.py, billing.py, clinical.py, config.py
│   ├── documents.py        # Consentimientos + PDFs + email docs
│   ├── backup.py           # Export/import DB
│   ├── finance.py, notifications.py, patients.py
│   ├── pages.py            # Rutas HTML + API notas
│   ├── treatments.py, users.py, waitlist.py, audit.py
├── templates/patients/
│   ├── detail.html         # Ficha paciente (historial, bonos, datos)
│   ├── documents.html      # Documentos adjuntos + Consentimientos firmados
│   ├── list.html, form.html
├── static/docs/            # Plantillas .docx de consentimientos
```

## Lo implementado en sesiones anteriores

### 1. Edición de documentos de cobro
- Icono lápiz en tabla de facturas → modal edición (tipo, importe, método pago, cita/bono)
- PUT `/api/billing/invoices/{id}` actualiza registro, elimina PDF antiguo, genera nuevo
- Schema `InvoiceUpdate` con campos: doc_type, amount, payment_method, is_paid, appointment_id, session_pack_id, clear_appointment, clear_session_pack

### 2. Registro automático de ingresos en contabilidad
- Al crear/marcar factura como pagada → se crea `FinanceEntry` tipo INCOME vinculada (campo `invoice_id` en finance_entries)
- Al desmarcar → se elimina el ingreso
- Al cambiar importe → se actualiza
- **Excepción**: pago con bono (session_pack_id + sin payment_method) NO genera ingreso (ya se generó al comprar el bono)
- Al editar precio de bono → se actualiza factura + ingreso + regenera PDF

### 3. Precios por defecto
- Tabla `config` (clave-valor): `default_session_price` y `default_pack_price`
- Se precargan en modal finalizar cita y formulario crear bono
- Configurables desde Configuración > General

### 4. Finalización de cita mejorada
- Si bono marcado en cita → modal finalización preselecciona "Bono" y oculta campo importe
- Fecha de sesión clínica = fecha de la cita (no fecha actual)
- Opción "Bono" en selector método pago (no se envía al backend, solo marca is_paid)

### 5. Backup (export/import)
- `POST /api/backup/export` — descarga .db (requiere contraseña admin)
- `POST /api/backup/import` — sube .db, reemplaza actual (guarda copia previa)
- UI en Configuración > Backup
- Router: `app/routers/backup.py`

### 6. Sistema de consentimientos informados
- **Plantillas**: archivos `.docx` en `app/static/docs/` con marcadores `{{campo}}`
- **Firma**: rellena plantilla con datos paciente + datos modal → convierte a PDF con `docx2pdf`
- **PDFs firmados**: se guardan en `C:\PoC\documentos_firmados` (configurable con `SIGNED_DOCS_PATH`)
- **Modelo `SignedConsent`**: patient_id, template_name, pdf_path, signed_at, signed_by, is_revoked, revoked_at, revocation_pdf_path
- **No se puede firmar dos veces** el mismo consentimiento (se filtra del desplegable)
- **Revocación**: genera nuevo PDF con sufijo `_revocacion`, marca original como revocado
- **UI**: en vista Documentos del paciente (Más... → Documentos)
- **Spinner**: overlay animado "Generando documento..." durante la conversión
- **Dependencias**: `python-docx`, `docx2pdf` (usa Word en Windows, LibreOffice en Linux)
- **Timezone**: UTC+2 (España) para fechas en documentos
- **Campos vacíos**: se rellenan con `____________________` para mantener espacio

#### Marcadores del documento CI FISIOTERAPIA GENERAL.docx:
**Firma principal**: `{{nombre_paciente}}`, `{{dni_paciente}}`, `{{día_firma}}`, `{{mes_firma}}`, `{{mes_firma_num}}`, `{{ano_firma}}`, `{{fisio_firma}}`, `{{dni_fisio_firma}}`, `{{ud_fisioterapia}}`, `{{observaciones}}`

**Autorización tutor** (solo si hay datos): `{{nombre_paciente_autorizado}}`, `{{dni_paciente_autorizado}}`, `{{día_firma_autorizado}}`, `{{mes_firma_autorizado}}`, `{{ano_firma_autorizado}}`, `{{nombre_tutor}}`, `{{dni_tutor}}`, `{{relacion_tutor}}`

**Revocación** (solo al revocar): `{{nombre_tutor_revoc}}`, `{{nombre_paciente_revoc}}`, `{{día_firma_revoc}}`, `{{mes_firma_num_revoc}}`, `{{ano_firma_revoc}}`, `{{observaciones_revoc}}`, `{{día_revoc}}`, `{{mes_revoc}}`, `{{ano_revoc}}`

#### Marcadores del documento CI PUNCION SECA.docx:
**Firma principal**: `{{nombre_paciente}}`, `{{dni_paciente}}`, `{{patología_paciente}}`, `{{día_firma}}`, `{{mes_firma}}`, `{{ano_firma}}`

**Autorización tutor** (solo si hay datos): `{{nombre_paciente_autorizado}}`, `{{dni_paciente_autorizado}}`, `{{nombre_tutor}}`, `{{dni_tutor}}`, `{{relacion_tutor}}`, `{{día_firma_autorizado}}`, `{{mes_firma_autorizado}}`, `{{ano_firma_autorizado}}`

**Revocación** (solo al revocar): `{{nombre_tutor_revoc}}`, `{{nombre_paciente_revoc}}`, `{{día_firma_revoc}}/{{mes_firma_num_revoc}}/{{ano_firma_revoc}}` (fecha firma original), `{{observaciones_revoc}}`, `{{día_revoc}}` de `{{mes_revoc}}` de `{{ano_revoc}}` (fecha actual)

### 7. Formulario dinámico de consentimientos
- El modal de firma muestra solo los campos relevantes según la plantilla seleccionada
- Configuración en frontend: diccionario `TEMPLATE_FIELDS` por nombre de fichero
- CI FISIOTERAPIA GENERAL: fisio_firma, dni_fisio_firma, ud_fisioterapia, observaciones
- CI PUNCION SECA: patología_paciente
- Campos comunes automáticos (nombre, DNI, fecha) no se piden
- Sección tutor siempre visible (opcional)

### 8. Notas de desarrollo
- Textarea al final de la página Documentación (`/docs/funcionalidades`)
- Se persiste en sección `## Notas` del `TODO.md`
- API: `GET/PUT /api/notes`

### 9. Tratamientos - iconos
- Reemplazados textos por iconos (ojo=ver PDF, sobre=email, lápiz=editar)
- PDF se abre con authFetch + blob (requiere token)

### 10. Documentación actualizada
- `funcionalidades.md` — documento principal de funcionalidades (se muestra en la app)
- `especificacion_tecnica.md` — modelos, stack, patrones
- `DESPLIEGUE_WINDOWS.md` — guía paso a paso
- `CONFIGURACION_PRODUCCION.md` — email IONOS, USB, consentimientos
- `TODO.md` — tareas (casi todas completadas)

## Lo implementado en sesiones anteriores (resumen adicional)

### 11. Ficha de paciente — campos clínicos ampliados
- Eliminados campos `allergies` y `notes` del formulario de paciente
- Añadido campo `motivo_consulta` (Text) — motivo de la consulta actual
- Añadido campo `anamnesis` (Text) — agrupa: patologías músculo-esqueléticas, otras patologías, cirugías, accidentes/fracturas, medicación habitual, alergias, ortodoncia/plantillas, deporte, profesión
- Añadido campo `tratamiento_contraindicaciones` (Text) — agrupa: tratamiento y contraindicaciones
- Los campos `allergies` y `notes` se mantienen en BD por compatibilidad pero ya no se usan en el formulario
- Migración: ALTER TABLE con columnas nuevas (SQLite no soporta DROP COLUMN en versiones antiguas)
- Vista `form.html` actualizada con secciones agrupadas visualmente

## Lo implementado en esta sesión

### 1. CI PUNCION SECA — consentimiento informado
- Soporte completo para la plantilla `CI PUNCION SECA.docx`
- Campo `patología_paciente` en el formulario (solo se muestra al seleccionar esta plantilla)
- Procesamiento de tablas en documentos .docx (además de párrafos, headers y footers)
- Revocación: `{{día_firma_revoc}}/{{mes_firma_num_revoc}}/{{ano_firma_revoc}}` usa la fecha de firma original del consentimiento
- Revocación: `{{día_revoc}}/{{mes_revoc}}/{{ano_revoc}}` usa la fecha actual

### 2. Tabla de configuración genérica
- **Eliminado** modelo `ClinicSettings` (tabla con una sola fila y columnas fijas)
- **Creado** modelo `Config` — tabla clave-valor (`key TEXT PRIMARY KEY`, `value TEXT`)
- Helpers: `get_config(db, key, default)` y `set_config(db, key, value)`
- Claves actuales: `default_duration`, `default_session_price`, `default_pack_price`, `whatsapp_template`
- Para añadir nuevas configuraciones no se requiere DDL ni migraciones

### 3. Recordatorio WhatsApp
- Botón "Enviar recordatorio" en el modal de cita (color WhatsApp + logo SVG)
- Abre WhatsApp Web con mensaje prellenado al teléfono del paciente
- El teléfono se formatea automáticamente a internacional España (34...)
- Mensaje configurable desde Configuración > General
- Variables disponibles: `{nombre}`, `{fecha}`, `{hora}`
- Usa `window.open(..., 'whatsapp')` para reutilizar la misma pestaña

### 4. Tests unitarios ampliados
- Nuevo fichero `tests/test_missing_coverage.py` con 29 tests
- Cobertura añadida: audit, users CRUD, waitlist (resolve/check-slot/patient-pending), notifications (mark read/delete), treatments (get/update/delete), clinical (update session), finance (list/update/delete entries), patients (deactivate), appointments (recurrence)
- Total: 95 tests (91 pasan, 4 fallan por dependencia COM/Word preexistente)

## Modelos de BD relevantes (añadidos/modificados)
- `FinanceEntry`: añadido `invoice_id` (FK invoices)
- `Config`: nuevo — tabla clave-valor para toda la configuración (reemplaza `ClinicSettings`)
- `SignedConsent`: nuevo (patient_id, template_name, pdf_path, signed_at, signed_by, is_revoked, revoked_at, revocation_pdf_path)

## Tests
- 95 tests en `tests/` (test_auth.py, test_billing.py, test_app.py, test_new_features.py, test_missing_coverage.py)
- Todos pasan excepto 4 de consentimiento que requieren Word abierto (COM/docx2pdf)

## Notas técnicas importantes
- La DB es `sante.db` en la raíz del proyecto
- Los PDFs de facturas están en `app/static/invoices/`
- `docx2pdf` necesita `pythoncom.CoInitialize()` en threads (ya implementado)
- El archivo `.docx` tiene marcadores divididos en múltiples runs de Word → la función `_replace_in_paragraph` reconstruye el texto completo y lo redistribuye
- El BOM del archivo `billing.py` requiere `encoding='utf-8-sig'` para parsear con ast
- `consent_generator.py` procesa también tablas del documento (no solo párrafos)
- El formulario de firma de consentimientos es dinámico: `TEMPLATE_FIELDS` en `documents.html` define qué campos mostrar por plantilla
- La configuración usa tabla `config` (key/value) — no requiere DDL para añadir nuevos parámetros
- WhatsApp: `window.open` con nombre fijo `'whatsapp'` reutiliza la pestaña si fue abierta por la app
