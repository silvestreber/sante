# Estimación de horas de desarrollo — Santé Fisioterapia

Documento elaborado a partir del análisis completo del código fuente, commits, documentación técnica, hoja de ruta, especificación técnica y funcionalidades implementadas.

---

## Metodología

La estimación se basa en:
- **Commit inicial**: 16.075 líneas de código añadidas en un solo commit (toda la base de la app ya estaba construida antes de empezar a usar git).
- **Commits posteriores**: 24 commits adicionales con 5.000+ líneas netas de cambios.
- **Documentación**: 6 documentos técnicos (especificación, hoja de ruta, despliegue, configuración producción, funcionalidades, contexto de desarrollo).
- **Infraestructura**: sistema de migraciones propio, scripts de despliegue con rollback, servicio systemd, política de USB, backup automático.
- **Tests**: suite de 95 tests unitarios distribuidos en 6 ficheros.

Se aplican rangos (mínimo–máximo) para reflejar la incertidumbre inherente a cualquier estimación retrospectiva.

---

## Desglose por área

### 1. Planificación y arquitectura (antes de escribir código)

| Tarea | Horas |
|-------|-------|
| Análisis de requisitos con el cliente | 4–6 |
| Definición del stack tecnológico y restricciones (Raspberry Pi, SQLite, sin frameworks JS) | 2–3 |
| Diseño del modelo de datos (18 tablas, relaciones, enums) | 4–6 |
| Redacción de la especificación técnica (`especificacion_tecnica.md`) | 3–4 |
| Redacción de la hoja de ruta en 12 fases (`hoja_de_ruta.md`) | 2–3 |
| **Subtotal** | **15–22 h** |

---

### 2. Backend — Núcleo y autenticación

| Tarea | Horas |
|-------|-------|
| Estructura del proyecto, `main.py`, `auth.py` (JWT, bcrypt, roles, `require_role`) | 4–6 |
| Modelos SQLAlchemy (18 tablas: User, Patient, Appointment, Invoice, SessionPack, ClinicalSession, Treatment, FinanceEntry, Notification, AuditLog, Schedule, SpecialSchedule, Holiday, PhysioSchedule, PhysioSpecialSchedule, WaitlistEntry, Config, PatientDocument) | 6–9 |
| Sistema de migraciones propio (`migrations/runner.py` + 8 versiones) | 4–6 |
| `init_db.py`, `database.py` (función `unaccent` registrada en SQLite) | 2–3 |
| Audit log (`audit_log.py`) integrado en todas las operaciones sensibles | 2–3 |
| **Subtotal** | **18–27 h** |

---

### 3. Backend — Routers (14 módulos)

| Router | Descripción | Horas |
|--------|-------------|-------|
| `patients.py` | CRUD pacientes, búsqueda flexible (unaccent + ilike), paginación, desactivación, paciente provisional, subida de documentos | 6–9 |
| `appointments.py` | CRUD citas, recurrencias, validación solapamiento, `check_schedule()`, `check_overlap()`, `out_of_hours` | 6–8 |
| `billing.py` | Facturas (3 tipos), bonos, numeración secuencial, edición con regeneración de PDF, integración contabilidad, pago pendiente | 8–12 |
| `clinical.py` | Historial clínico, sesiones (normales y manuales), justificante de asistencia | 4–6 |
| `config.py` | Horario semanal, horarios especiales, festivos, horario fisio, horario especial fisio, ausencias, `calendar-constraints`, configuración general, almacenamiento configurable, check-conflicts | 10–14 |
| `documents.py` | Consentimientos informados, firma manuscrita, revocación, documentos adjuntos, generación PDFs en blanco | 8–12 |
| `finance.py` | Ingresos, gastos, balance por periodo | 3–4 |
| `notifications.py` | Avisos internos, WebSocket tiempo real, reconexión automática | 4–6 |
| `waitlist.py` | Lista de espera, preferencias, detección de huecos al cancelar | 4–6 |
| `audit.py` | Log de actividad con filtros | 2–3 |
| `users.py` | CRUD usuarios, firma del fisio, desactivación | 3–4 |
| `treatments.py` | Tratamientos y ejercicios, generación PDF | 2–3 |
| `backup.py` | Export/import BD, protección con contraseña | 2–3 |
| `auth.py` | Login, logout, renovación de token | 1–2 |
| **Subtotal** | **67–102 h** |

---

### 4. Backend — Servicios transversales

| Tarea | Horas |
|-------|-------|
| `pdf.py`: generación de PDFs (facturas, justificantes, tratamientos, justificante de asistencia, marca de agua, pie de página institucional, firma del fisio) | 8–12 |
| `consent_generator.py`: relleno de plantillas `.docx`, estampado de firma manuscrita, conversión multiplataforma (Word en Windows, LibreOffice headless en Linux), procesamiento de tablas/párrafos/headers/footers | 10–15 |
| `email_service.py`: SMTP, adjuntos PDF, nombre de clínica como remitente | 2–3 |
| `reminders.py`: recordatorio automático 24h antes por email, backup automático (luego migrado a cron) | 3–4 |
| `storage.py`: rutas configurables, movimiento seguro de ficheros (copiar-verificar-borrar), comprobación de espacio y colisiones, política USB (error 503 si no montado) | 6–9 |
| `websocket_manager.py`: gestión de conexiones WebSocket por usuario | 2–3 |
| **Subtotal** | **31–46 h** |

---

### 5. Frontend — Templates (22 vistas)

| Vista | Descripción | Horas |
|-------|-------------|-------|
| `base.html` | Layout, navbar, sidebar hamburguesa, lógica de token, WebSocket, toast, modales de confirmación, `checkAuth`, `setupNav`, `authFetch` | 6–8 |
| `login.html` | Formulario, mostrar/ocultar contraseña | 1–2 |
| `calendar.html` | FullCalendar (mes/semana/día), modal crear/editar cita, slots disponibles por fisio, citas recurrentes, lista de espera, finalizar cita, bono, WhatsApp, justificante de asistencia, festivos naranja, citas fuera de horario, horario especial fisio, constraints dinámicas | 25–35 |
| `patients/list.html` | Lista paginada, búsqueda flexible, filtros, paginación con "Ir a página", recuperar página al volver | 3–4 |
| `patients/detail.html` | Ficha con toggle Ficha/Historial, alergias destacadas, bono activo, aviso pago pendiente, paciente provisional, historial clínico integrado | 6–9 |
| `patients/form.html` | Formulario completo (datos personales + campos clínicos ampliados: motivo consulta, anamnesis, contraindicaciones) | 3–4 |
| `patients/documents.html` | Subida múltiple con drag & drop, lista de documentos, consentimientos informados, canvas de firma manuscrita, spinner de generación | 6–9 |
| `patients/packs.html` | Gestión completa de bonos (crear, editar, cancelar, historial) | 4–6 |
| `billing/patient.html` | Registrar pago, toggle Cita/Bono, historial de documentos, editar documento, enviar por email | 5–7 |
| `config/schedule.html` | Horario semanal, horarios especiales, festivos, horario fisio, horario especial fisio (tabla dinámica por rango), ausencias, configuración general, almacenamiento, backup, importar/exportar, modal de conflictos, validación inline, botón limpiar fila | 15–20 |
| `audit/list.html` | Log con filtros, paginación numérica con "Ir a página" | 2–3 |
| `finance/list.html` | Ingresos/gastos, balance por periodo | 3–4 |
| `notifications/list.html` | Avisos, marcar leído, eliminar | 2–3 |
| `users/list.html` | CRUD usuarios, firma del fisio, selector de color | 3–4 |
| `treatments/list.html` + `form.html` | Tratamientos, generación PDF | 2–3 |
| `billing/list.html` | Lista de facturas global | 1–2 |
| `waitlist/list.html` | Lista de espera completa | 2–3 |
| `dashboard.html` | Panel básico | 1 |
| **Subtotal** | **90–131 h** |

---

### 6. Infraestructura y despliegue

| Tarea | Horas |
|-------|-------|
| `deploy.sh`: backup previo, git pull, dependencias, migraciones, reinicio servicio, healthcheck con reintentos, rollback automático ante fallo | 5–7 |
| Configuración systemd (`sante.service`), IP fija, firewall UFW | 2–3 |
| Montaje permanente USB en `/etc/fstab`, estructura de carpetas, permisos | 2–3 |
| Permisos sudo acotados para reinicio de servicio y apagado desde la app | 1–2 |
| `backup_db.sh`: backup diario/mensual vía cron, rotación de copias antiguas | 2–3 |
| Configuración SMTP IONOS en producción | 1–2 |
| Pruebas en Raspberry Pi (arranque, LibreOffice, USB, firma, email) | 4–6 |
| **Subtotal** | **17–26 h** |

---

### 7. Tests

| Tarea | Horas |
|-------|-------|
| `conftest.py`: fixtures (BD de test, tokens, client HTTP) | 2–3 |
| `test_app.py`: tests generales (483 líneas) | 4–6 |
| `test_auth.py`: autenticación | 1–2 |
| `test_billing.py`: facturación y bonos (263 líneas) | 3–4 |
| `test_consents_and_backup.py`: consentimientos y backup (389 líneas) | 3–5 |
| `test_new_features.py`: nuevas funcionalidades (339 líneas) | 3–4 |
| `test_missing_coverage.py`: cobertura adicional (458 líneas, 29 tests) | 3–5 |
| **Subtotal** | **19–29 h** |

---

### 8. Documentación técnica

| Documento | Descripción | Horas |
|-----------|-------------|-------|
| `especificacion_tecnica.md` | Stack, modelos, patrones, roles, arquitectura (551 líneas) | 3–4 |
| `hoja_de_ruta.md` | 12 fases de desarrollo con dependencias (256 líneas) | 2–3 |
| `funcionalidades.md` | Manual de usuario completo, actualizado iterativamente | 4–6 |
| `DESPLIEGUE.md` | Guía completa de despliegue (Parte A/B/C, 411 líneas) | 3–4 |
| `DESPLIEGUE_WINDOWS.md` | Guía de entorno de desarrollo en Windows | 2–3 |
| `CONFIGURACION_PRODUCCION.md` | Email IONOS, USB, consentimientos, verificación final | 2–3 |
| `CONTEXTO_DESARROLLO.md` | Contexto técnico para continuación de sesiones | 2–3 |
| `TODO.md` | Seguimiento de tareas, decisiones, plan de producción | 2–3 |
| **Subtotal** | **20–29 h** |

---

## Resumen global

| Área | Mínimo | Máximo |
|------|-------:|-------:|
| 1. Planificación y arquitectura | 15 h | 22 h |
| 2. Backend — Núcleo y autenticación | 18 h | 27 h |
| 3. Backend — Routers (14 módulos) | 67 h | 102 h |
| 4. Backend — Servicios transversales | 31 h | 46 h |
| 5. Frontend — Templates (22 vistas) | 90 h | 131 h |
| 6. Infraestructura y despliegue | 17 h | 26 h |
| 7. Tests | 19 h | 29 h |
| 8. Documentación técnica | 20 h | 29 h |
| **TOTAL** | **277 h** | **412 h** |

---

## Estimación central

> **~340 horas de desarrollo** (punto medio del rango 277–412 h)

Equivale aproximadamente a:
- **8,5 semanas** a jornada completa (40 h/semana)
- **17 semanas** a media jornada (20 h/semana)
- **4–5 meses** de desarrollo real con interrupciones, reuniones con el cliente y ciclos de prueba/corrección

---

## Notas sobre la estimación

- El **commit inicial** (906e9e1) incluye 16.075 líneas de código en 78 ficheros, lo que indica que una parte muy significativa del desarrollo se realizó antes de empezar a usar git de forma sistemática. Esto hace que la estimación sea necesariamente retrospectiva para esa parte.
- El **frontend es el área más costosa** (90–131 h): el calendario (`calendar.html`) es especialmente complejo, con más de 1.500 líneas de JavaScript vanilla que integran FullCalendar, lógica de slots, horarios de fisios, lista de espera, finalización de citas, bonos y múltiples modales.
- Los **consentimientos informados** (`consent_generator.py`) fueron técnicamente los más complejos: manipulación de XML interno de `.docx`, estampado de firma manuscrita, compatibilidad multiplataforma Word/LibreOffice, y múltiples ciclos de corrección de bugs.
- El **sistema de almacenamiento configurable** (`storage.py`) implicó un refactor transversal de todos los módulos que escriben ficheros.
- No se incluyen horas de **reuniones con el cliente**, **formación en el uso de la app** ni **soporte post-despliegue**, que añadirían entre 20 y 40 horas adicionales.
