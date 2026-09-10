# TODO — Santé

Tareas pendientes tras la primera presentación con el cliente.

---

## Facturación y bonos

- [x] **Configurar caducidad de bonos** — Añadir fecha de expiración a los bonos de sesiones.
- [x] **Documento de cobro asociado a cita o bono** — El documento se asocia a una cita o a un bono. Se genera PDF, se guarda en servidor, se puede ver, editar y enviar por email.
- [x] **Tipos de pago: efectivo y bizum** — Solo Efectivo y Bizum. Si se elige método = pagado, si no = pendiente.
- [x] **Generar facturas** — Completar la generación de facturas desde la app.

## Calendario y sesiones

- [x] **Registrar datos de sesión desde la cita del calendario** — Al hacer clic en una cita, poder registrar lo realizado en la sesión, consumir sesión de bono y crear informe directamente.
- [x] **Info de bono en modal de cita** — Al editar una cita se muestra si el paciente tiene bono activo y sesiones restantes. Checkbox para marcar si se quiere consumir sesión. Botón "Finalizar cita" (solo visible en citas confirmadas) que consume la sesión del bono si está marcado.
- [x] **Lista de espera** — Implementada como modal en el calendario. Soporta múltiples fisios, franja horaria, día concreto o rango, prioridad, y detección automática de coincidencias al cancelar citas.
- [x] **Filtros de estado en calendario** — Checkboxes para pendientes/confirmadas con diferenciación visual por opacidad.
- [x] **Calendario por defecto del fisio** — Si el usuario es PHYSIO, ve solo sus citas al entrar.
- [x] **Forzar citas fuera de horario** — Botón "Guardar de todas formas" cuando la cita está fuera del horario de apertura.
- [x] **Aviso de fecha pasada** — Modal de confirmación al intentar crear una cita en fecha/hora anterior a la actual, con opciones de guardar, editar fecha o cancelar.

## Integraciones externas

- [ ] **Integrar con plantilla Excel existente** 
- [x] **Copia de seguridad** — Exportar e importar base de datos completa desde Configuración > Backup. Protegido con contraseña.
- [x] **Integrar email para recordatorios** — Configurado SMTP de Gmail (misma cuenta que ffrace). Pendiente cambiar a IONOS cuando el cliente proporcione los datos. Ver instrucciones en `DESPLIEGUE_WINDOWS.md`.
- [x] **Email con nombre de clínica como remitente** — Se usa `formataddr` (RFC 2047) para que el destinatario vea el nombre de la clínica en vez de solo la dirección de email.
- [x] **Avisos en tiempo real** — WebSocket para notificaciones instantáneas con sonido y toast, sin refresco de página.

## UI / Branding

- [x] **Integrar colores corporativos** — Fondo `#e4d3b9`, primario `#012d5e`. Aplicado en toda la app.
- [x] **Integrar logo** — Logo en login, navbar y como marca de agua de fondo.
- [x] **Bordes corporativos** — Todos los recuadros blancos e inputs con borde azul corporativo.
- [x] **Selectores y checkboxes custom** — Estilo propio acorde con la estética de la app.
- [x] **Modales de confirmación** — Sustituidos todos los `alert()`/`confirm()` por modales estilizados.
- [x] **Selector de color por fisio** — Configurable desde gestión de usuarios.

## Documentación y legal

- [x] **Firma de consentimiento de protección de datos** — Implementar flujo de firma del consentimiento (digital o registro de firma en papel).

## Otros cambios implementados

- [x] **Login case-insensitive** — El campo usuario no distingue mayúsculas/minúsculas.
- [x] **Modal de avisos al login** — Solo se muestra si hay avisos pendientes.
- [x] **Filtro pagos pendientes en pacientes** — Toggle para ver solo pacientes con facturas impagadas.
- [x] **Eliminar avisos** — Papelera con modal de confirmación.
- [x] **Avisos leídos/no leídos** — Diferenciación visual con borde grueso, negrita y botón "Marcar leído".
- [x] **Rol PHYSIO marca is_physio automáticamente** — Al seleccionar rol Fisioterapeuta en el formulario de usuario, el checkbox "Puede atender pacientes" se marca solo.
- [x] **Fisio preseleccionado al crear cita** — Si el usuario logueado es fisio, el selector de fisioterapeuta se preselecciona con él mismo al crear una nueva cita.
- [x] **Desactivar pacientes (borrado lógico)** — Botón para desactivar pacientes desde la lista (solo admin/recepción). Se conservan todos los datos. Toggle para ver pacientes no activos.
- [x] **Justificante de asistencia en historial** — Botones "Ver" y "Enviar por email" en cada sesión del historial clínico. Genera PDF con fecha, hora y duración de la cita.
- [x] **Historial clínico accesible para todos los roles** — Todos los usuarios pueden ver el historial y finalizar citas, no solo fisios.
- [x] **Registrar pago desde historial clínico** — El badge "Pendiente" es un enlace que abre modal para completar el pago (Efectivo/Bizum).

## Pendiente

- [x] **Carga de pacientes desde Excel** — Leer datos de pacientes desde un fichero Excel y guardarlos en la base de datos. Definir columnas esperadas, gestionar duplicados y mostrar resumen del resultado.
- [ ] **Exportar facturación a Excel para gestoría** — Generar un Excel con los datos de facturación (facturas, importes, métodos de pago, fechas) en el formato que requiere la gestoría.
- [x] **Horario personal de fisio con mañana y tarde** — Ampliar el horario semanal de cada fisioterapeuta para que tenga franja de mañana y franja de tarde, igual que el horario de la clínica.
- [ ] **Tabla de permisos por rol y revisión de RECEPTION** — Crear una tabla que documente a qué funcionalidades puede acceder cada rol (ADMIN, RECEPTION, PHYSIO). Revisar y ajustar los permisos actuales del rol RECEPTION.


- [x] **Poner documentos reales de consentimiento** — Sustituir los documentos de consentimiento actuales por los definitivos del cliente.
- [x] **Rellenar documentos de consentimiento en la firma** — Completar automáticamente los datos del paciente en el documento al firmar.

- [x] **Refactor calendario en fin de semana** — Si la fecha actual es sábado o domingo, el calendario muestra la semana siguiente (lunes) por defecto.
- [x] **Quitar documentos de la vista del paciente** — Documentos movidos a vista propia accesible desde el menú de acciones.
- [x] **Simplificar bonos en vista del paciente** — Muestra solo resumen del bono activo (sesiones consumidas/restantes y caducidad) como tabla clicable que lleva a la vista completa de bonos. Icono de advertencia rojo si tiene pago pendiente con modal para registrar pago. Botón "Crear bono" si no tiene. La gestión completa (crear, editar, cancelar, historial) está en `/patients/{id}/packs`.
- [x] **Refactor modal editar cita** — Estado como texto (no selector). Dos filas de botones: confirmar/finalizar + cancelar, y guardar cambios + cerrar. Citas finalizadas quedan en solo lectura. Icono de pago pendiente del bono con modal para registrar pago.
- [x] **Lógica de cancelación de bonos** — Si el bono estaba pagado, se elimina el documento de cobro y se revierte el ingreso en contabilidad. Si estaba pendiente, no se toca. Comprobación automática diaria de caducidad.
- [x] **Añadir historial clínico a la vista principal del paciente** — Historial integrado directamente en la ficha del paciente. Eliminado del menú de acciones.

## Decisiones tomadas

- ~~WhatsApp~~: Descartado. Requiere cuenta Business API y no compensa.
- **Email IONOS**: Solo para envío de recordatorios. Más adelante se valorará lectura de bandeja.
- **Almacenamiento**: USB montada en la Raspberry Pi (descartado WD My Cloud Home por ser demasiado cerrado).

## Implementado en esta sesión (27/05/2026)

- [x] **Marcadores unificados en consentimientos** — Todos los documentos usan los mismos marcadores (`{{nombre_paciente}}`, `{{dni_paciente}}`, etc.).
- [x] **Campo DNI en modal de firma** — Si el paciente no tiene DNI en su ficha, se pide en el formulario de firma.
- [x] **Eliminado campo consentimiento genérico** — Quitado `consent_signed`/`consent_date` de pacientes. Toda la gestión de consentimientos en su apartado.
- [x] **Vista documentos muestra todos los consentimientos** — Firmados (Vigente), revocados (Revocado con fecha) y no firmados (No firmado con plantilla en blanco).
- [x] **PDFs en blanco pre-generados** — Se generan al arrancar la app, se sirven instantáneamente.
- [x] **Re-firma tras revocación** — Borra registros y PDFs antiguos, crea nuevo desde cero.
- [x] **Backup automático diario** — A las 02:00 hora España, sobreescribe copia diaria. Día 1 del mes persiste copia mensual.
- [x] **Rutas parametrizables** — `SIGNED_DOCS_PATH`, `INVOICES_PATH`, `PATIENT_DOCS_PATH`, `LOG_PATH`, `AUTO_BACKUP_PATH` configurables en `.env`.
- [x] **Filtrado archivos temporales Word** — Los `~$*.docx` no aparecen en el listado de plantillas.
- [x] **Anti-cache en visualización PDFs** — Timestamp en peticiones para evitar blobs cacheados.

## Notas

Test note content

---

# PLAN DE TRABAJO — Producción en Raspberry Pi (pendiente)

> Bloque añadido para retomar en una sesión nueva de Kiro (por si crashea).
> Contexto: app FastAPI + SQLite ("Santé") desplegada EN PRODUCCIÓN en una Raspberry Pi
> con datos reales de pacientes. EXTREMA PRUDENCIA: nada destructivo, backup antes de tocar prod.

## Entorno de producción (datos reales verificados)

- Usuario del sistema: `silver`  (home: `/home/silver`)
- Proyecto: `/home/silver/sante`
- Virtualenv: `/home/silver/venv`  (FUERA del proyecto)
- Servicio systemd: `sante.service` (`User=silver`), depende de `media-usb.mount`
- SO: Raspberry Pi OS Lite, base Debian 13 (trixie), SOLO consola (sin escritorio)
- IP actual: `192.168.0.100`, puerto app `8000`
- Base de datos: `/home/silver/sante/sante.db`
- El backup por app (Configuración) exporta SOLO el `.db`; los PDFs en disco NO se incluyen.
- Desarrollo en Windows (`C:\PoC\sante`). OJO: hay rutas y dependencias Windows-only en el código.
- Mac del usuario: se quiere integrar con una carpeta compartida (ver tarea 5).
- Repositorio git: https://github.com/silvestreber/sante.git (rama `main`). Commit inicial subido.
  `.gitignore` excluye datos sensibles: `.db`, `.env`, `*.xlsx`, backups, uploads, PDFs de facturas, logs.

## Tareas pendientes (en orden, con cuidado en producción)

- [~] **1. Despliegue fácil (script de actualización)** — EN PROGRESO
  Hecho: proyecto subido a repo git privado en GitHub (commit inicial, rama `main`), con `.gitignore`
  que protege datos sensibles.
  Pendiente: conectar `/home/silver/sante` de la Raspberry con el repo; crear script `deploy.sh` que
  haga backup del `.db` → `git pull` → instalar dependencias si cambió `requirements.txt` → aplicar
  migraciones si hacen falta → reiniciar `sante` → verificar healthcheck. Decidir sistema de
  migraciones: actualmente NO hay (la BD se crea con `Base.metadata.create_all` en
  `app/db/init_db.py`, que crea tablas nuevas pero NO altera columnas existentes). Proponer Alembic o
  estrategia incremental segura que NO borre datos. Backup del `.db` antes de migrar SIEMPRE.
  NOTA: la guía menciona `python seed.py` pero no se encuentra ese fichero en dev; verificar en la Pi.

- [ ] **2. Rutas de almacenamiento configurables desde la app**
  Inventario COMPLETO de todas las rutas donde la app escribe ficheros, indicando cuáles van a la
  microSD y cuáles al USB externo. Permitir configurarlas desde la vista de Configuración (no desde
  código ni `.env`) para poder cambiar de USB cuando se llene. Puntos conocidos:
  - Documentos firmados: `SIGNED_DOCS_PATH` (env, default `"C:/PoC/documentos_firmados"` — ruta Windows!)
  - Facturas PDF: se generan en `tempfile` temporal; hay copias en `app/static/invoices/`
  - Backups: carpeta `backups/` (symlink a USB montado en `media-usb.mount` según guía)
  - Uploads de pacientes: variable `UPLOADS_PATH`/`PATIENT_DOCS_PATH` en `.env`
  NOTA: el TODO dice que ya hay rutas parametrizables por `.env`, pero NO desde la vista de
  Configuración; eso es lo que falta. Los puntos de montaje deben ser FIJOS y persistir tras reiniciar
  (fstab o unit `.mount` de systemd). Indicar explícitamente qué ficheros acaban en SD vs USB.

- [ ] **3. Política de la app respecto al USB externo**
  Documentar y, si hace falta, mejorar el comportamiento cuando:
  - el USB NO está enchufado al arrancar (hoy `sante.service` depende de `media-usb.mount`, así que
    la app NO arranca sin USB — confirmar y decidir si es lo deseado).
  - el USB se desenchufa con la app funcionando (escrituras, errores, integridad de datos).
  Incluir cómo consultar la capacidad máxima del USB actual para comprar otro igual o mayor.

- [ ] **4. BUG: error al generar documentos en la Raspberry**
  CAUSA PROBABLE ya detectada en `app/consent_generator.py -> convert_docx_to_pdf()`: usa
  `import pythoncom` + `docx2pdf`, que dependen de Microsoft Word vía COM y SOLO funcionan en Windows.
  En Linux (Raspberry) fallan. Además `SIGNED_DOCS_PATH` por defecto es `"C:/PoC/documentos_firmados"`
  (ruta Windows inexistente en la Pi). Sustituir la conversión docx->PDF por algo compatible con Linux
  (p.ej. LibreOffice headless `soffice --convert-to pdf`) y corregir la ruta de salida por una
  configurable (ver tarea 2). Las facturas/tratamientos usan FPDF (`app/pdf.py`), multiplataforma, así
  que probablemente esas SÍ funcionen — verificar igualmente.

- [ ] **5. Carpeta compartida Mac ↔ USB de la Raspberry**
  Estudiar la viabilidad de una carpeta compartida en el Mac enlazada directamente con la unidad
  externa (USB) de la Raspberry, de forma bidireccional: soltar documentos en la carpeta del Mac y que
  aparezcan en la Raspberry, y traer documentos de la Raspberry al Mac. Objetivo: manipular los
  documentos de forma masiva y cómoda, sin tener que hacerlo uno a uno por la app (cada documento está
  asociado a un usuario/paciente). Opciones a evaluar: Samba (SMB, nativo en macOS Finder "Conectar a
  servidor" `smb://192.168.0.100`), o `rsync`/`scp` para sincronización puntual. Considerar seguridad
  (son datos de salud): acceso solo en red local, credenciales, permisos de usuario `silver`, y que
  NO se rompa el enlace `media-usb.mount` ni los permisos que la app necesita para escribir.

## Reglas de trabajo

- No ejecutar nada destructivo. Backup del `.db` y de los PDFs antes de tocar producción.
- El usuario ejecuta los comandos en la Raspberry (SSH/teclado) y pega la salida; Kiro guía.
- Confirmar cada paso en producción antes de aplicarlo.
- Empezar leyendo el código relevante antes de proponer cambios.
