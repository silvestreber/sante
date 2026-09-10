# Especificación técnica — Santé (Gestión de clínica de fisioterapia)

---

## Contexto

Aplicación web para gestionar una clínica de fisioterapia. Se ejecutará en una Raspberry Pi 3 Model B (4 cores ARM @ 1.2GHz, 1GB RAM). La solución debe ser ligera y eficiente dado los recursos limitados.

Los usuarios accederán desde el navegador (móvil y PC) dentro de la red local de la clínica.

---

## Stack tecnológico

### Backend
- **Python 3.10+**
- **FastAPI** como framework web (ligero, async, rápido)
- **Uvicorn** como servidor ASGI (`uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 3`)
- **SQLAlchemy** como ORM
- **SQLite** como base de datos (archivo local, sin servidor adicional)
- **bcrypt** para hash de contraseñas
- **python-jose** para JWT (autenticación por tokens)
- **python-dotenv** para variables de entorno (.env)
- **Jinja2** para templates HTML server-side
- **weasyprint** o **fpdf2** para generación de PDFs (facturas, justificantes, ejercicios, consentimientos)
- **smtplib** (stdlib) para envío de emails con adjuntos

### Frontend
- **Tailwind CSS** vía CDN (`https://cdn.tailwindcss.com`) — sin build step
- **HTMX** (`https://unpkg.com/htmx.org`) — para actualizaciones parciales sin SPA
- **FullCalendar** (`https://cdn.jsdelivr.net/npm/fullcalendar`) — para el calendario de citas
- **JavaScript vanilla** para lógica del cliente
- Sin frameworks JS (React, Vue, etc.) — demasiado pesado para este contexto

### Testing
- **pytest** + **httpx** para tests unitarios de la API

---

## Estructura del proyecto

```
sante/
├── .env                        # Variables de entorno (credenciales SMTP, SECRET_KEY, etc.)
├── requirements.txt            # Dependencias Python
├── app/
│   ├── __init__.py
│   ├── main.py                 # Punto de entrada FastAPI, registro de routers
│   ├── auth.py                 # Autenticación (hash, verify, JWT, roles)
│   ├── schemas.py              # Schemas Pydantic (request/response)
│   ├── pdf.py                  # Generación de PDFs (facturas, justificantes, ejercicios, consentimientos)
│   ├── email_service.py        # Envío de emails con adjuntos PDF
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py         # Engine SQLAlchemy, SessionLocal, get_db
│   │   ├── models.py           # Modelos SQLAlchemy (todos)
│   │   └── init_db.py          # Crear tablas + usuario admin por defecto
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py             # Login/logout
│   │   ├── pages.py            # Rutas de páginas HTML (templates)
│   │   ├── patients.py         # CRUD pacientes
│   │   ├── appointments.py     # CRUD citas + citas recurrentes
│   │   ├── clinical.py         # Historial, sesiones, informes
│   │   ├── billing.py          # Pagos, facturas, bonos
│   │   ├── finance.py          # Ingresos, gastos, balance (solo admin)
│   │   ├── users.py            # Gestión de usuarios (solo admin)
│   │   ├── treatments.py       # Tratamientos y ejercicios
│   │   ├── notifications.py    # Avisos internos + WebSocket tiempo real
│   │   ├── waitlist.py         # Lista de espera
│   │   ├── audit.py            # Log de actividad (solo admin)
│   │   └── config.py           # Configuración: horarios, festivos (solo admin)
│   ├── static/
│   │   ├── img/                # Logo, iconos
│   │   ├── css/                # Estilos custom si los hay
│   │   └── js/                 # Scripts auxiliares (calendar config, etc.)
│   ├── templates/
│   │   ├── base.html           # Layout base
│   │   ├── login.html          # Página de login
│   │   ├── dashboard.html      # Panel principal
│   │   ├── patients/           # Templates de pacientes
│   │   ├── appointments/       # Templates de citas/calendario
│   │   ├── clinical/           # Templates de historial/informes
│   │   ├── billing/            # Templates de facturación
│   │   ├── finance/            # Templates de contabilidad
│   │   ├── users/              # Templates de gestión de usuarios
│   │   ├── treatments/         # Templates de tratamientos
│   │   ├── config/             # Templates de configuración
│   │   └── partials/           # Fragmentos HTML para HTMX
│   ├── uploads/ -> /mnt/usb/sante/uploads/  # Symlink a USB externa
│   └── logs/
│       └── errors.log          # Log de errores
├── pdf_templates/              # Plantillas base para PDFs (factura, justificante, etc.)
└── tests/
    ├── conftest.py             # Fixtures (DB de test, tokens, client)
    └── test_*.py               # Tests por módulo
```

---

## Modelos de base de datos

### User (usuarios del sistema)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| username | String unique | |
| password_hash | String | bcrypt |
| full_name | String | |
| role | Enum | ADMIN, RECEPTION, PHYSIO |
| is_physio | Boolean | Indica si puede atender pacientes (independiente del rol) |
| color | String nullable | Color hex para identificar al fisio en el calendario |
| is_active | Boolean | Para desactivar sin eliminar |
| created_at | DateTime | |

### Patient (pacientes)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| first_name | String | |
| last_name | String | |
| phone | String | |
| email | String nullable | |
| address | String nullable | |
| birth_date | Date nullable | |
| dni | String nullable | |
| allergies | Text nullable | Alergias y contraindicaciones (campo destacado) |
| consent_signed | Boolean | Si firmó consentimiento informado |
| consent_date | Date nullable | Fecha de firma |
| notes | Text nullable | Notas generales |
| created_at | DateTime | |

### PatientDocument (documentos adjuntos)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| patient_id | FK Patient | |
| filename | String | Nombre del archivo |
| filepath | String | Ruta en uploads/ |
| description | String nullable | |
| uploaded_at | DateTime | |

### Appointment (citas)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| patient_id | FK Patient | |
| physio_id | FK User | Fisioterapeuta asignado |
| start_time | DateTime | |
| duration_minutes | Integer | 30, 45, 60 (default: 45) |
| location | Enum | CLINIC, HOME |
| status | Enum | PENDING, CONFIRMED, CANCELLED, NO_SHOW |
| notes | Text nullable | Notas de la cita |
| recurrence_group | String nullable | ID para agrupar citas recurrentes |
| created_by | FK User | Quién creó la cita |

### Session (registro de cada sesión clínica)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| patient_id | FK Patient | |
| appointment_id | FK Appointment nullable | |
| physio_id | FK User | |
| date | DateTime | |
| techniques | Text | Técnicas aplicadas |
| observations | Text nullable | |
| evolution | Text nullable | Evolución del paciente |

### ClinicalReport (informes clínicos)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| patient_id | FK Patient | |
| physio_id | FK User | |
| report_type | Enum | INITIAL_ASSESSMENT, FOLLOW_UP, DISCHARGE |
| content | Text | Contenido del informe |
| created_at | DateTime | |
| updated_at | DateTime nullable | |

### Treatment (tratamientos/ejercicios para casa)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| patient_id | FK Patient | |
| physio_id | FK User | |
| title | String | |
| description | Text | Ejercicios, recomendaciones |
| created_at | DateTime | |

### Invoice (documentos de cobro)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| patient_id | FK Patient | |
| appointment_id | FK Appointment nullable | Cita asociada |
| session_pack_id | FK SessionPack nullable | Bono asociado |
| invoice_number | String unique | Numeración secuencial |
| doc_type | Enum | INVOICE, SIMPLIFIED_INVOICE, RECEIPT |
| amount | Float | |
| payment_method | Enum nullable | CASH, BIZUM |
| is_paid | Boolean | |
| created_at | DateTime | |

### SessionPack (bonos de sesiones)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| patient_id | FK Patient | |
| total_sessions | Integer | Sesiones compradas |
| used_sessions | Integer | Sesiones consumidas |
| price | Float | Precio del bono |
| created_at | DateTime | |
| expires_at | Date nullable | |

### FinanceEntry (ingresos y gastos — solo admin)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| entry_type | Enum | INCOME, EXPENSE |
| amount | Float | |
| description | String | |
| category | String nullable | |
| date | Date | |
| created_by | FK User | |

### Notification (avisos internos)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| from_user_id | FK User | |
| to_user_id | FK User | |
| message | Text | |
| is_read | Boolean | |
| created_at | DateTime | |

### AuditLog (registro de actividad — solo admin)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| user_id | FK User | |
| action | String | Ej: "Creó cita", "Editó paciente" |
| entity | String | Ej: "Patient", "Appointment" |
| entity_id | Integer nullable | |
| timestamp | DateTime | |
| details | Text nullable | Info adicional |

### Schedule (horario semanal normal)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| day_of_week | Integer | 0=Lunes, 6=Domingo |
| morning_open | String nullable | HH:MM |
| morning_close | String nullable | HH:MM |
| afternoon_open | String nullable | HH:MM |
| afternoon_close | String nullable | HH:MM |
| is_closed | Boolean | Día cerrado |

### SpecialSchedule (horarios especiales por periodo)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| name | String | Nombre del periodo (ej: "Verano") |
| date_from | Date | Inicio del periodo |
| date_to | Date | Fin del periodo |
| day_of_week | Integer | 0=Lunes, 6=Domingo |
| morning_open | String nullable | HH:MM |
| morning_close | String nullable | HH:MM |
| afternoon_open | String nullable | HH:MM |
| afternoon_close | String nullable | HH:MM |
| is_closed | Boolean | |

### Holiday (días festivos)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| date | Date unique | Fecha del festivo |
| name | String nullable | Nombre (ej: "Navidad") |

### ClinicSettings (configuración general)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | Tabla de una sola fila |
| default_duration | Integer | Duración predeterminada de cita en minutos (default: 45) |
| default_session_price | Float | Precio por defecto de una sesión (default: 0) |
| default_pack_price | Float | Precio por defecto de un bono (default: 0) |

### PhysioSchedule (horario personal de fisioterapeuta)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| user_id | FK User | |
| day_of_week | Integer | 0=Lunes, 6=Domingo |
| start_time | String nullable | HH:MM |
| end_time | String nullable | HH:MM |
| is_off | Boolean | Día libre |

### WaitlistEntry (lista de espera)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| patient_id | FK Patient | |
| physio_ids | String nullable | IDs separados por coma, None = cualquiera |
| time_preference | Enum | ANY, MORNING, AFTERNOON, CUSTOM |
| time_from | String nullable | HH:MM (solo si CUSTOM) |
| time_to | String nullable | HH:MM (solo si CUSTOM) |
| date_from | Date nullable | Desde qué fecha le vale |
| date_to | Date nullable | Hasta qué fecha (o mismo día si es día concreto) |
| asap | Boolean | Lo antes posible |
| priority | Boolean | Prioritario (se ordena antes) |
| notes | Text nullable | |
| is_resolved | Boolean | |
| created_by | FK User | |
| created_at | DateTime | |

### SignedConsent (consentimientos firmados)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | Integer PK | |
| patient_id | FK Patient | |
| template_name | String | Nombre del archivo plantilla (.docx) |
| pdf_path | String | Ruta del PDF firmado generado |
| signed_at | DateTime | Fecha y hora de la firma |
| signed_by | FK User | Quién registró la firma |

---

## Roles y permisos

| Funcionalidad | ADMIN | RECEPTION | PHYSIO |
|---------------|:-----:|:---------:|:------:|
| Configuración (horarios, festivos) | ✓ | ✗ | ✗ |
| Gestión de pacientes | ✓ | ✓ | ✓ |
| Calendario y citas | ✓ | ✓ | ✓ |
| Facturación y pagos | ✓ | ✓ | ✓ |
| Bonos de sesiones | ✓ | ✓ | ✓ |
| Tratamientos | ✓ | ✓ | ✓ |
| Envío de PDFs por email | ✓ | ✓ | ✓ |
| Avisos internos | ✓ | ✓ | ✓ |
| Historial clínico | ✓ | ✗ | ✓ |
| Informes clínicos | ✓ | ✗ | ✓ |
| Registro de sesiones | ✓ | ✗ | ✓ |
| Contabilidad (ingresos/gastos/balance) | ✓ | ✗ | ✗ |
| Gestión de usuarios | ✓ | ✗ | ✗ |
| Log de actividad | ✓ | ✗ | ✗ |

---

## Patrones y metodologías

### Autenticación
- JWT con tokens en localStorage del navegador.
- Roles: ADMIN, RECEPTION, PHYSIO (Enum de Python).
- Campo `is_physio` (Boolean) independiente del rol: indica si el usuario puede atender pacientes, acceder al historial clínico y aparecer en el selector de fisioterapeutas del calendario.
- Middleware `require_role(*roles)` como dependencia de FastAPI.
- Dependencia `require_physio` que valida `is_physio=True` independientemente del rol.
- Contraseñas hasheadas con bcrypt.
- Token enviado en header `Authorization: Bearer <token>`.
- Expiración del token: 1 hora. Si el token caduca y el usuario intenta acceder a cualquier funcionalidad, el backend responde con 401 (permiso denegado) y el frontend redirige automáticamente al login.
- El campo de usuario en el login no es case-sensitive (se normaliza a minúsculas).

### Frontend con HTMX
- Páginas principales renderizadas server-side con Jinja2.
- La vista principal tras el login es el calendario (no un dashboard intermedio).
- Actualizaciones parciales (listas, tablas, formularios) con HTMX:
  - `hx-get="/partials/endpoint"` para cargar fragmentos.
  - `hx-target="#container"` para indicar dónde insertar.
  - `hx-include="[name='filtro']"` para enviar filtros.
- Calendario con FullCalendar (JS), comunicándose con la API REST para CRUD de citas.
- Lógica de autenticación y formularios complejos con JS vanilla.

### Calendario
- FullCalendar renderiza las citas obtenidas de `/api/appointments?start=X&end=Y`.
- Slots de 1 hora fijos (`slotDuration: 01:00:00`). La duración de las citas es independiente del tamaño del slot.
- Al entrar tras login, se muestra un modal con el número de avisos sin leer solo si hay avisos pendientes.
- Un solo click en un hueco abre directamente el modal para crear cita (sin selección previa de rango).
- Botón "Nueva cita" junto al título para crear citas cuando los slots están ocupados.
- Botón "Lista de espera" que abre un modal con la lista completa y formulario de añadir.
- Click en una cita abre modal para ver/editar.
- Filtros (clínica/domicilio, fisioterapeuta, estado pendiente/confirmada) se aplican en frontend.
- Si el usuario es PHYSIO, el filtro de fisio se preselecciona con su propio ID.
- Cada fisioterapeuta tiene un color asignado (campo `color` en User). Las citas se pintan con el color del fisio.
- Las citas pendientes se muestran con opacidad reducida (60%) para diferenciarlas de las confirmadas.
- `slotEventOverlap: false` para que citas simultáneas se muestren lado a lado.
- Validación de solapamiento en backend antes de guardar.
- Validación de horario en backend: no se permiten citas fuera del horario de apertura ni en festivos. Si se intenta, se muestra error con botón "Guardar de todas formas" para forzar.
- Los días de la semana siempre cerrados (configurados con `is_closed`) se ocultan del calendario (`hiddenDays`).
- `slotMinTime` y `slotMaxTime` se ajustan exactamente a la hora de apertura y cierre configurados.
- La pausa de mediodía se colapsa en un único bloque compacto (24px) con etiqueta de rango horario (ej: "13:30-16:00"), no clickable.
- Los días festivos se muestran con fondo gris y no permiten crear citas.
- El endpoint `/api/config/calendar-constraints` proporciona al frontend toda la información de horarios, festivos, días ocultos y hora de cierre.
- Validación de horario personal del fisioterapeuta en frontend: si la cita cae fuera de su horario se muestra aviso con confirmación (pero se permite guardar).
- Al cancelar una cita, se comprueba automáticamente si hay pacientes en lista de espera que encajen con el hueco liberado.
- Al crear una cita, se comprueba si el paciente está en lista de espera y se ofrece eliminarlo.

### Generación de PDFs
- Plantillas HTML renderizadas con Jinja2 y convertidas a PDF.
- Tipos: factura, factura simplificada, justificante, consentimiento informado, tratamiento/ejercicios.
- Se almacenan en `static/invoices/` con nombre = número de documento.
- Al editar un documento de cobro (PUT `/api/billing/invoices/{id}`), se elimina el PDF antiguo y se regenera con los datos actualizados.

### Consentimientos informados
- Plantillas `.docx` con marcadores `{{campo}}` en `app/static/docs/`.
- Al firmar, se rellena la plantilla con datos del paciente (nombre, DNI, fecha) y datos del modal (fisio, tutor, observaciones).
- Se convierte a PDF con `docx2pdf` (usa Microsoft Word en Windows, LibreOffice en Linux).
- Los PDFs firmados se guardan en el directorio configurado (`SIGNED_DOCS_PATH`, por defecto `C:/PoC/documentos_firmados`).
- Un paciente puede firmar múltiples consentimientos de distintos tipos.
- Dependencias: `python-docx` para manipular .docx, `docx2pdf` para convertir a PDF.

### Envío de emails
- SMTP (Gmail u otro) configurado en .env.
- Se adjunta el PDF generado.
- Usado para: envío manual de documentos + recordatorio automático de cita (24h antes).

### Recordatorio automático de citas
- Tarea en background (threading daemon) que cada hora revisa citas de las próximas 24h.
- Envía email de recordatorio al paciente si tiene email registrado.
- Marca la cita como "recordatorio enviado" para no duplicar.

### Notificaciones en tiempo real (WebSocket)
- Conexión WebSocket en `/api/notifications/ws?token=<jwt>` para recibir avisos instantáneos.
- Al recibir un aviso: se reproduce un sonido (Web Audio API) y se muestra un toast.
- Reconexion automática silenciosa si se pierde la conexión (sin recargar la página).
- No se reintenta si el token es inválido/expirado (código 4001).
- Gestor de conexiones (`websocket_manager.py`) que mantiene las conexiones activas por usuario.

### UI / Branding
- Colores corporativos: fondo `#e4d3b9`, primario `#012d5e`.
- Logo en: pantalla de login, navbar (invertido a blanco), y como marca de agua de fondo (opacidad 6%).
- Todos los recuadros blancos tienen borde corporativo (`border-2 border-sante-primary/40`).
- Inputs, selects y cuadros de búsqueda con borde corporativo.
- Selectores custom con flecha en color corporativo.
- Checkboxes custom con estilo propio (no default del navegador).
- Modales de confirmación con estilo de la app (no `alert()` ni `confirm()` nativos).

### Base de datos
- SQLite (un solo archivo .db, sin servidor).
- SQLAlchemy con `declarative_base()`.
- `create_all()` al arrancar para crear tablas.
- Dependencia `get_db()` con yield para gestionar sesiones.

### Rendimiento (Raspberry Pi)
- Caché en memoria para endpoints frecuentes (TTL 3-5 segundos).
- Arrancar con 3 workers: `uvicorn ... --workers 3`.
- Evitar queries N+1, cargar datos en batch.
- Templates HTML ligeros, sin frameworks JS pesados.
- Paginación en listas largas (pacientes, historial).

### Gestión de errores
- Handler global de excepciones que loguea a archivo con timestamp, contexto y traceback.
- `logging.basicConfig(filename="app/logs/errors.log", level=logging.ERROR)`

### Seguridad
- Todos los endpoints de escritura protegidos con roles.
- Credenciales en .env (nunca hardcodeadas).
- Archivos de pacientes (uploads/) no accesibles directamente por URL, se sirven a través de endpoint protegido.
- Log de auditoría para operaciones sensibles.

### UI/UX
- Diseño mobile-first (se usa mucho desde el móvil en la clínica).
- Tema claro y limpio (contexto sanitario, no tema oscuro).
- Colores corporativos de la clínica.
- Modales para confirmaciones y formularios de edición.
- Notificaciones toast (pop-up temporal arriba a la derecha) para feedback de acciones (éxito/error), sin usar `alert()` del navegador.
- Filtros en tiempo real en el frontend (sin peticiones al back cuando sea posible).
- Indicador visual de alergias/contraindicaciones en la ficha del paciente.
- Badge de notificaciones no leídas en la navegación.
- Navegación mediante menú lateral tipo hamburguesa (sidebar) para maximizar el espacio del calendario.

### Almacenamiento externo (USB)
- Los documentos adjuntos de pacientes se almacenan en una memoria USB montada permanentemente en `/mnt/usb/`.
- Ruta real de uploads: `/mnt/usb/sante/uploads/`.
- En el proyecto se usa un symlink: `app/uploads/ -> /mnt/usb/sante/uploads/`.
- La ruta se configura en .env (`UPLOADS_PATH=/mnt/usb/sante/uploads`) para flexibilidad.
- Al arrancar, la app verifica que la USB está montada y la ruta es accesible. Si no lo está, loguea un error crítico y deshabilita la subida de archivos (no se cae la app entera).

### Backup y resiliencia
- Exportar base de datos como backup (copia del archivo .db). Protegido con contraseña del usuario admin.
- Importar backup: sube un archivo .db que reemplaza la base de datos actual. Se guarda copia automática del estado previo antes de restaurar. Protegido con contraseña.
- Al restaurar se eliminan todos los datos actuales y se reemplazan por los del archivo importado.
- Accesible desde Configuración > Backup (solo admin).
- El backup también se guarda en la carpeta `backups/`.

---

## requirements.txt

```
fastapi
uvicorn[standard]
sqlalchemy
bcrypt
python-jose[cryptography]
python-multipart
jinja2
python-dotenv
fpdf2
markdown
python-docx
docx2pdf
pytest
httpx
```

---

## Variables de entorno (.env)

```
SECRET_KEY=clave-secreta-cambiar-en-produccion
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=clinica@gmail.com
SMTP_PASSWORD=app-password-aqui
SMTP_FROM=clinica@gmail.com
CLINIC_NAME=Santé Fisioterapia
CLINIC_PHONE=600000000
CLINIC_ADDRESS=Calle Ejemplo 1, Ciudad
CLINIC_CIF=B12345678
UPLOADS_PATH=/mnt/usb/sante/uploads
BACKUPS_PATH=/mnt/usb/sante/backups
```

---

## Notas para despliegue en Raspberry Pi

- Conectar por cable Ethernet (no WiFi).
- Arrancar como servicio systemd para auto-inicio.
- No instalar dependencias innecesarias.
- Monitorizar RAM con `htop`.
- Considerar rotación de logs (logrotate).
- SQLite es perfecto para esta escala (pocos usuarios concurrentes).

### Configuración de la USB externa

1. Formatear la USB en ext4 (mejor compatibilidad con Linux que FAT32/NTFS).
2. Montar permanentemente añadiendo entrada en `/etc/fstab`:
   ```
   UUID=xxxx-xxxx /mnt/usb ext4 defaults,nofail 0 2
   ```
   - `nofail` evita que la Raspberry no arranque si la USB no está conectada.
3. Crear la estructura de carpetas:
   ```bash
   mkdir -p /mnt/usb/sante/uploads
   mkdir -p /mnt/usb/sante/backups
   ```
4. Crear symlink en el proyecto:
   ```bash
   ln -s /mnt/usb/sante/uploads app/uploads
   ```
5. La app valida al arrancar que `/mnt/usb` está montado (comprueba que no es un directorio vacío del sistema de archivos raíz).
