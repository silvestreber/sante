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

- [x] **1. Despliegue fácil (script de actualización)** — COMPLETADO
  Hecho: repo git privado en GitHub (rama `main`) con `.gitignore` que protege datos sensibles.
  Raspberry vinculada al repo. `deploy.sh` creado: backup del `.db` → `git pull` → deps si cambió
  `requirements.txt` → migraciones → reiniciar `sante` → healthcheck con reintentos (20x2s=40s, la
  app tarda ~11s en arrancar) → resumen final OK/FALLO. Sistema de migraciones ligeras propio en
  `migrations/` (runner.py + versions/, NO Alembic; idempotente, no destructivo). Guía unificada en
  `DESPLIEGUE.md`. La BD se crea sola al arrancar (`init_db()` en el lifespan); no existe `seed.py`.

- [x] **2. Rutas de almacenamiento configurables desde la app** — COMPLETADO
  Ahora las rutas se configuran desde **Configuración > Almacenamiento** (solo ADMIN), no solo por `.env`.
  Implementación:
  - Nuevo módulo `app/storage.py`: resuelve cada ruta base con prioridad tabla `Config` → `.env` →
    default por SO (Linux `/media/usb/...`). Genera **nombres únicos globales** (prefijo 8 hex) para que
    dos categorías nunca colisionen. Movimiento seguro (comprueba espacio + colisiones, estrategia
    copiar-verificar-borrar por tamaño de bytes, con rollback; el origen no se toca hasta verificar).
  - Cada documento guarda en BD la **ruta relativa** (nombre de fichero); la absoluta se reconstruye
    como base(Config) + relativa. Refactorizados: consentimientos (`consent_generator.py`,
    `documents.py`), facturas (`billing.py`, nueva columna `Invoice.pdf_filename`), uploads de
    pacientes (`patients.py`, estructura plana), backups automáticos (`reminders.py`).
  - **Logs se quedan en la SD** (`main.py`, default relativo al proyecto). Lo demás (documentos,
    facturas, uploads, backups) va al USB.
  - Endpoints en `config.py`: GET storage-paths (con espacio libre), preview, apply (mueve en
    background), progress (polling), restart-service. UI: pestaña con tabla, barra de progreso, lista
    de colisiones y botón de reinicio del servicio.
  - Migración `0002_storage_paths`: añade `invoices.pdf_filename` y siembra las rutas de la Pi en
    `Config` (idempotente).
  - Reinicio del servicio desde la app: requiere permiso sudo acotado para `silver` (ver `DESPLIEGUE.md`
    sección B.13). Se cambió el default Windows de las rutas (relacionado con el bug de la tarea 4).
  Verificado en local: tests auth (6/6) y billing (16/16) OK; flujo de rutas probado end-to-end.

- [x] **3. Política de la app respecto al USB externo** — COMPLETADO
  Política decidida e implementada: la app **solo escribe en el USB**; si el punto de montaje no
  está activo, devuelve un error controlado (HTTP 503) y NO escribe nada (nunca en la SD).
  - `storage.py`: `is_mounted`/`requires_mount`/`StorageUnavailableError`; `get_base_path` exige
    USB montado antes de escribir (verificado en la Pi: ruta real montada=True, ruta fantasma=False).
  - Handler global 503 en `main.py` con mensaje claro. En facturas se comprueba ANTES de tocar la BD
    (no se crean registros sin PDF).
  - Correción sobre lo que creíamos: el servicio usa `Wants=media-usb.mount` (no `Requires=`) y el
    fstab usa `nofail`, así que **la app SÍ arranca sin USB**; solo se bloquea guardar documentos.
  - Indicador en Configuración > Almacenamiento: estado montado/no conectado, capacidad libre/total,
    aviso rojo si falta un USB. USB actual: SanDisk Cruzer Blade ~29 GB (28.6 GB, 27 libres).
  - `DESPLIEGUE.md`: política del USB y procedimiento completo de cambio de USB (lleno o reemplazo).

- [x] **4. BUG: error al generar documentos en la Raspberry** — COMPLETADO
  `convert_docx_to_pdf()` en `app/consent_generator.py` ahora es multiplataforma:
  - En **Linux** (Raspberry): LibreOffice headless (`soffice --headless --convert-to pdf --outdir`,
    con perfil de usuario temporal `-env:UserInstallation` y timeout 120s). LibreOffice ya estaba
    instalado en la Pi (v25.2.3, `/usr/bin/soffice`). Probada la conversión real en la Pi: OK.
  - En **Windows** (desarrollo): sigue usando docx2pdf/Word. `docx2pdf` marcado como dependencia
    solo-Windows en `requirements.txt` (`; sys_platform == "win32"`).
  - `_find_soffice()` localiza soffice/libreoffice (o `SOFFICE_BIN`) y da error claro si falta.
  - La ruta de salida ya es configurable (resuelto en la tarea 2; el default Windows se corrigió allí).
  - Facturas/tratamientos usan FPDF (multiplataforma), ya funcionaban. Esto desbloquea la FIRMA DE
    CONSENTIMIENTOS y la generación de PDFs en blanco en la Pi.

- [x] **5. Gestión de documentos del paciente (unificada)** — COMPLETADO
  DECISIÓN: se descartó la carpeta compartida por red (Samba/rsync) por el problema de asociar
  documentos sueltos a su paciente y por seguridad (datos de salud). En su lugar, TODO se gestiona
  desde la app, subiendo desde la ficha del paciente (así siempre se sabe de quién es).
  Implementado:
  - Documentos y consentimientos UNIFICADOS en la tabla `patient_documents`. Se eliminó la lógica de
    estados (firmado/vigente/revocado) y los endpoints all-consents, consent-revoke, signed-consents.
    `SignedConsent` queda sin uso (tabla vacía). Migración `0003_unificar_documentos` (idempotente).
  - Vista "Documentos": una sola lista con el nombre de cada documento. Nombre clicable: si es PDF se
    abre en pestaña nueva, si es otro tipo se descarga. Acciones: enviar por email y eliminar (borra
    BD + fichero del disco, con confirmación).
  - Subida MÚLTIPLE con arrastrar y soltar: lista previa (nombre + X para quitar), botón subir, barra
    de progreso y confirmación. Descripción ya no obligatoria. Nombre único interno en disco.
  - Firmar consentimiento: se mantiene, y ahora crea un documento más. Incluye opción "Generar
    documento de revocación" (campos de revocación rellenos, originales vacíos) como una variante.
  - WhatsApp descartado para documentos: WhatsApp Web solo permite texto, no adjuntar ficheros por URL
    (requeriría Business API); enviar un enlace sería un riesgo de privacidad. Solo email.
  - Verificado en local: subida múltiple, abrir PDF, descargar otro tipo, eliminar, email. Firma con
    LibreOffice se probará en la Pi (en Windows la conversión no está disponible). Suite de tests OK
    (86 pasan; los de firma se saltan en Windows).

- [x] **6. Firma manuscrita de consentimientos (en tablet/móvil/ratón)** — COMPLETADO
  Implementado: canvas de firma grande en el modal (dedo/ratón vía pointer events), la firma se estampa
  DENTRO del PDF a ancho fijo (5 cm) sustituyendo los marcadores `{{firma_paciente}}` y `{{firma_tutor}}`
  de las plantillas (no se guarda imagen aparte). Firma del paciente siempre; la del tutor solo si se
  rellenan datos de tutor. Los .docx llevan los marcadores. Desplegado en la Pi (blank PDFs regenerados).
  Además se corrigió que `generate_blank_pdfs()` bloqueaba el arranque: ahora corre en hilo aparte.
  (Spec original del enfoque debajo, como referencia.)
  Objetivo: poder firmar FÍSICAMENTE el consentimiento en el mismo acto, capturando la firma en un
  recuadro y estampándola en el PDF. El uso principal será con tablet (firma con el dedo), pero debe
  funcionar también con ratón (escritorio) y en móvil.

  Contexto del flujo actual (ya implementado):
  - Al firmar un consentimiento se abre un modal que pide los datos que requiere cada plantilla
    (endpoint `/api/documents/consent-templates`; firma en `POST /api/documents/consent-sign/{patient_id}`).
  - `app/consent_generator.py`: `fill_consent_template()` rellena la plantilla `.docx` con los datos
    (marcadores `{{...}}`), y `generate_signed_consent()` convierte a PDF (LibreOffice en Linux, tarea 4).
    El PDF se guarda en el USB con nombre único y su ruta relativa en `SignedConsent.pdf_path`.

  Qué añadir:
  1. **Recuadro de firma en el modal**: un `<canvas>` HTML donde el paciente firme con el dedo
     (eventos touch/pointer) o con el ratón. Botones "Borrar" y confirmar. Capturar la firma como
     imagen PNG (base64, fondo transparente o blanco). Valorar librería ligera tipo signature_pad
     (sin dependencias) frente a implementación propia con la Canvas API.
  2. **Enviar la firma al backend** junto con el resto de datos del formulario (campo con el PNG en
     base64). Ampliar el schema de firma (`ConsentSignRequest` en `app/routers/documents.py`).
  3. **Estampar la firma en el PDF**, SIEMPRE en la misma posición (al final del documento) y al mismo
     tamaño, independientemente del contenido. Decidir enfoque técnico:
     - Opción A: insertar la imagen en el `.docx` (python-docx) en un marcador de firma reservado
       antes de convertir a PDF. Requiere que las plantillas tengan un hueco/marcador de firma.
     - Opción B: generar el PDF como ahora y luego estampar la imagen en la última página con una
       librería PDF (p.ej. pypdf + reportlab, o pdf overlay). Más control de posición/tamaño exacto,
       independiente de la plantilla. Probablemente la más robusta para "siempre mismo tamaño y sitio".
     Definir tamaño fijo del recuadro de firma (p.ej. ancho x alto en mm) y su posición (margen inferior).
  4. **Consideraciones**: la firma es un dato personal sensible -> va al USB dentro del PDF, no se
     guarda la imagen suelta. Mantener compatibilidad con el flujo sin firma (algunos documentos podrían
     firmarse en papel). Verificar que el estampado funciona en la Pi (Linux) end-to-end.
  5. Añadir dependencias nuevas a `requirements.txt` si hacen falta (reportlab/pypdf, multiplataforma).

## Reglas de trabajo

- No ejecutar nada destructivo. Backup del `.db` y de los PDFs antes de tocar producción.
- El usuario ejecuta los comandos en la Raspberry (SSH/teclado) y pega la salida; Kiro guía.
- Confirmar cada paso en producción antes de aplicarlo.
- Empezar leyendo el código relevante antes de proponer cambios.
