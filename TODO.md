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
