# Hoja de ruta — Santé (Desarrollo)

---

## Fase 1: Cimientos del proyecto

**Objetivo:** Tener la app arrancando con autenticación funcional y estructura base.

1. Crear la estructura de carpetas del proyecto.
2. Configurar `requirements.txt` y `.env`.
3. Implementar `database.py` (engine, sesión, get_db).
4. Crear el modelo `User` con roles (ADMIN, RECEPTION, PHYSIO).
5. Implementar `init_db.py` (crear tablas + usuario admin por defecto).
6. Implementar `auth.py` (hash, verify, JWT con expiración de 1h, require_role).
7. Crear el router de login (`/api/auth/login`).
8. Crear `base.html` (layout con Tailwind, HTMX, navegación, lógica de token).
9. Crear `login.html` y su lógica JS.
10. Crear `dashboard.html` básico (redirige al calendario como vista principal post-login).
11. Configurar el handler global de errores y logging.
12. Verificar que todo arranca y el login funciona.

**Entregable:** App arrancando, login funcional, dashboard vacío con navegación según rol.

---

## Fase 2: Gestión de pacientes

**Objetivo:** CRUD completo de pacientes con búsqueda y ficha detallada.

1. Crear modelo `Patient`.
2. Crear modelo `PatientDocument`.
3. Crear router `patients.py` con endpoints:
   - Listar pacientes (con paginación).
   - Buscar/filtrar (nombre, apellidos, teléfono).
   - Crear paciente (formulario de registro).
   - Ver ficha de paciente.
   - Editar paciente.
4. Crear templates: lista de pacientes, formulario de registro, ficha del paciente.
5. Implementar subida de documentos adjuntos (a la USB externa).
6. Endpoint protegido para servir documentos adjuntos.
7. Campo destacado de alergias/contraindicaciones visible en la ficha.
8. Registro de consentimiento informado (checkbox + fecha).

**Entregable:** Se pueden registrar pacientes, buscarlos, ver su ficha y adjuntar documentos.

---

## Fase 3: Calendario y citas

**Objetivo:** Calendario visual con creación, edición y gestión de citas.

1. Crear modelo `Appointment`.
2. Crear router `appointments.py` con endpoints:
   - Listar citas por rango de fechas (para FullCalendar).
   - Crear cita (con validación de solapamiento).
   - Editar cita (cambiar hora, estado, notas).
   - Cancelar cita.
   - Crear citas recurrentes.
3. Integrar FullCalendar en el template del calendario.
4. Modal para crear cita al hacer clic en un hueco.
5. Modal para ver/editar cita al hacer clic en una cita existente.
6. Filtros: clínica/domicilio, por fisioterapeuta.
7. Estados de cita: pendiente, confirmada, cancelada, no asistió.
8. Asignación de fisioterapeuta y duración (por defecto 45 minutos).
9. Campo de notas en la cita.

**Entregable:** Calendario funcional con citas visibles, creación, edición, filtros y control de solapamiento.

---

## Fase 4: Historial clínico y sesiones

**Objetivo:** El fisioterapeuta puede registrar lo que hace en cada visita y crear informes.

1. Crear modelo `Session` (registro por visita).
2. Crear modelo `ClinicalReport`.
3. Crear router `clinical.py` con endpoints:
   - Ver historial completo de un paciente (sesiones + informes).
   - Registrar sesión (técnicas, observaciones, evolución).
   - Crear informe (con selección de plantilla: valoración inicial, seguimiento, alta).
   - Editar informe.
4. Templates: historial del paciente, formulario de sesión, formulario de informe.
5. Acceso restringido a ADMIN y PHYSIO.

**Entregable:** El fisio puede registrar cada sesión y crear/editar informes clínicos desde la ficha del paciente.

---

## Fase 5: Tratamientos y ejercicios

**Objetivo:** Crear tratamientos con ejercicios/recomendaciones para el paciente.

1. Crear modelo `Treatment`.
2. Crear router `treatments.py` con endpoints:
   - Crear tratamiento (título + descripción con ejercicios).
   - Ver tratamientos de un paciente.
   - Editar tratamiento.
3. Templates: lista de tratamientos, formulario de creación/edición.
4. Vinculación desde la ficha del paciente.

**Entregable:** Se pueden crear tratamientos con ejercicios y verlos desde la ficha del paciente.

---

## Fase 6: Facturación y bonos

**Objetivo:** Registrar pagos, generar documentos de cobro y gestionar bonos de sesiones.

1. Crear modelo `Invoice`.
2. Crear modelo `SessionPack` (bonos).
3. Crear router `billing.py` con endpoints:
   - Registrar pago (método: efectivo, tarjeta, transferencia).
   - Crear documento de cobro (factura, factura simplificada, justificante).
   - Ver facturas de un paciente.
   - Crear bono de sesiones.
   - Consumir sesión de un bono.
   - Ver estado de bonos activos.
   - Ver pacientes con pagos pendientes.
4. Numeración secuencial automática de facturas.
5. Templates: formulario de pago, lista de facturas, gestión de bonos.

**Entregable:** Se pueden cobrar sesiones, generar facturas/justificantes y gestionar bonos.

---

## Fase 7: Generación de PDFs y envío por email

**Objetivo:** Generar documentos en PDF y enviarlos por email al paciente.

1. Implementar `pdf.py` con generación de PDFs:
   - Factura / factura simplificada.
   - Justificante de asistencia.
   - Consentimiento informado.
   - Tratamiento / ejercicios.
2. Plantillas HTML para cada tipo de PDF (con datos de la clínica desde .env).
3. Implementar `email_service.py` (conexión SMTP + envío con adjunto).
4. Botón "Enviar por email" en cada documento generado.
5. Botón "Descargar PDF" como alternativa.

**Entregable:** Se pueden generar PDFs de todos los documentos y enviarlos por email al paciente.

---

## Fase 8: Contabilidad (solo administración)

**Objetivo:** El admin puede gestionar ingresos, gastos y ver balances.

1. Crear modelo `FinanceEntry`.
2. Crear router `finance.py` con endpoints:
   - Registrar ingreso o gasto.
   - Editar entrada.
   - Eliminar entrada.
   - Ver balance por periodo (mensual, trimestral, anual, personalizado).
3. Templates: formulario de ingreso/gasto, vista de balance con totales.
4. Acceso restringido a ADMIN.

**Entregable:** El admin puede llevar la contabilidad básica de la clínica.

---

## Fase 9: Gestión de usuarios (solo administración)

**Objetivo:** El admin puede dar de alta, editar y desactivar usuarios.

1. Crear router `users.py` con endpoints:
   - Listar usuarios.
   - Crear usuario (asignar rol).
   - Editar usuario.
   - Desactivar usuario (sin eliminar).
2. Templates: lista de usuarios, formulario de creación/edición.
3. Acceso restringido a ADMIN.

**Entregable:** El admin gestiona quién tiene acceso a la aplicación.

---

## Fase 10: Avisos internos y recordatorios

**Objetivo:** Comunicación entre usuarios y recordatorios automáticos a pacientes.

1. Crear modelo `Notification`.
2. Crear router `notifications.py` con endpoints:
   - Enviar aviso a un compañero.
   - Ver mis avisos (leídos/no leídos).
   - Marcar como leído.
3. Badge de notificaciones no leídas en la navegación.
4. Implementar tarea en background para recordatorios de cita:
   - Cada hora revisa citas de las próximas 24h.
   - Envía email de recordatorio si el paciente tiene email.
   - Marca como enviado para no duplicar.

**Entregable:** Los usuarios pueden enviarse avisos y los pacientes reciben recordatorio de cita por email.

---

## Fase 11: Log de actividad (solo administración)

**Objetivo:** Registro de quién hizo qué y cuándo, por seguridad y cumplimiento legal.

1. Crear modelo `AuditLog`.
2. Crear router `audit.py` con endpoint para consultar el log (con filtros por usuario, fecha, acción).
3. Integrar el registro de auditoría en las operaciones sensibles de toda la app:
   - Crear/editar/eliminar pacientes.
   - Crear/cancelar citas.
   - Registrar pagos.
   - Crear/editar informes.
   - Gestión de usuarios.
4. Template: vista del log con filtros.
5. Acceso restringido a ADMIN.

**Entregable:** El admin puede ver un historial completo de acciones realizadas en la aplicación.

---

## Fase 12: Backup y despliegue final

**Objetivo:** Sistema de backup automático y puesta en producción en la Raspberry Pi.

1. Implementar backup automático de la base de datos a la USB (`/mnt/usb/sante/backups/`).
2. Envío del backup por email (con detección de cambios por hash MD5).
3. Tarea en background (daemon thread) para ejecutar backup periódico.
4. Validación al arrancar de que la USB está montada.
5. Crear servicio systemd para auto-inicio.
6. Configurar `/etc/fstab` para montaje permanente de la USB.
7. Pruebas de rendimiento en la Raspberry Pi.
8. Ajustes finales de UI/UX tras pruebas reales en la clínica.

**Entregable:** App desplegada en la Raspberry Pi, con backup automático y arranque al encender.

---

## Resumen visual

| Fase | Qué se construye | Depende de |
|------|-------------------|------------|
| 1 | Estructura + Auth + Login | — |
| 2 | Pacientes | Fase 1 |
| 3 | Calendario y citas | Fase 1, 2 |
| 4 | Historial clínico | Fase 2, 3 |
| 5 | Tratamientos | Fase 2 |
| 6 | Facturación y bonos | Fase 2 |
| 7 | PDFs y email | Fase 5, 6 |
| 8 | Contabilidad | Fase 1 |
| 9 | Gestión de usuarios | Fase 1 |
| 10 | Avisos y recordatorios | Fase 1, 3 |
| 11 | Log de actividad | Todas las anteriores |
| 12 | Backup y despliegue | Todas las anteriores |

---

## Notas

- Cada fase se puede probar de forma independiente antes de pasar a la siguiente.
- Las fases 8, 9 y 10 son independientes entre sí y se pueden desarrollar en paralelo tras la fase 3.
- La fase 11 se hace al final porque necesita integrarse con todas las operaciones existentes.
- La fase 12 es el cierre: todo lo que tiene que ver con poner la app en producción real.
