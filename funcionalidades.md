# Funcionalidades de la aplicación de gestión de clínica

---

## Funciones comunes (todos los usuarios)

### Sesión y autenticación

- La sesión del usuario caduca automáticamente tras 1 hora de inactividad (desde el último inicio de sesión).
- Si el usuario intenta acceder a cualquier funcionalidad con la sesión caducada, se le deniega el acceso y se le redirige a la pantalla de login.

### Pacientes

- Registrar un nuevo paciente rellenando un formulario con sus datos personales.
- Ver la lista completa de pacientes.
- Buscar pacientes por nombre, apellidos o teléfono.
- Desactivar pacientes (borrado lógico): el paciente deja de aparecer en la lista pero se conservan todos sus datos, historial, citas y facturas. Solo disponible para admin y recepción.
- Ver pacientes no activos: toggle en la lista de pacientes para mostrar los desactivados. Desde ahí se pueden reactivar.
- Ver la ficha de un paciente con todos sus datos (nombre, dirección, teléfono, etc.).
- Registrar alergias y contraindicaciones de forma destacada en la ficha del paciente (por ejemplo: marcapasos, alergias a materiales, etc.).
- Adjuntar documentos a la ficha del paciente (radiografías, informes médicos externos, fotos de evolución, etc.). Descripción obligatoria. Se pueden ver directamente en el navegador. Accesible desde el menú Acciones > Documentos.
- Registrar la firma del consentimiento informado directamente desde la ficha del paciente (botón "Firmar" con confirmación y fecha automática).
- Menú desplegable "Acciones" con acceso a: Historial clínico, Tratamientos, Facturación y Editar.

### Calendario y citas

- Al iniciar sesión, la vista principal de la aplicación es el calendario.
- Al entrar al calendario tras login, se muestra un modal informando de los avisos sin leer solo si hay uno o más pendientes. Si no hay avisos, no se muestra nada.
- Ver un calendario con todas las citas programadas.
- Los slots del calendario son de 1 hora. La pausa de mediodía se muestra como un único bloque compacto en gris con las horas indicadas (ej: "13:30-16:00").
- Un solo clic en un hueco del calendario abre directamente el modal para crear la cita en esa hora.
- Botón "Nueva cita" junto al título del calendario para crear citas sin depender de hacer clic en un hueco libre.
- Filtrar el calendario para ver solo citas en clínica o solo citas a domicilio.
- Filtrar por estado: checkboxes "Pendientes" y "Confirmadas" (ambos activos por defecto).
- Las citas pendientes se muestran con opacidad reducida para diferenciarlas visualmente de las confirmadas.
- Las citas de cada fisioterapeuta se muestran siempre en su color asignado, sin superposición visual (las citas simultáneas se muestran lado a lado).
- Si el usuario tiene rol PHYSIO, el calendario muestra por defecto solo sus citas.
- Crear una cita haciendo clic en el calendario, indicando:
  - Paciente (buscador con autocompletado integrado)
  - Fisioterapeuta asignado (si el usuario es fisio, se preselecciona a sí mismo)
  - Duración (30 min, 45 min, 1 hora) — por defecto según configuración
  - Lugar (clínica o domicilio)
- Al editar una cita se muestra el estado actual como texto (no editable). Botones: "Confirmar cita" (solo si pendiente), "Finalizar" (solo si confirmada y no finalizada), "Cancelar cita", "Guardar cambios" y "Cerrar".
- Las citas finalizadas (con sesión clínica registrada), canceladas o con "No asistió" se muestran en solo lectura sin botones de acción.
- Al editar una cita, se muestra información del bono del paciente (si tiene bono activo y sesiones restantes). Icono de advertencia rojo si el bono tiene pago pendiente, con modal para registrar el pago. Checkbox para marcar si se quiere consumir sesión.
- Crear citas recurrentes (por ejemplo: "todos los martes y jueves a las 10:00 durante 4 semanas").
- El calendario impide que se solapen citas del mismo fisioterapeuta.
- El backend valida que no se puedan crear citas fuera del horario de apertura ni en días festivos. Si se intenta, se muestra el error con opción de "Guardar de todas formas" para excepciones.
- Si se intenta crear una cita en una fecha y hora anterior a la actual, se muestra un modal informando con tres opciones: guardar de todas formas, editar fecha o cancelar.
- Los días de la semana que están siempre cerrados (ej: sábado y domingo) no aparecen en el calendario.
- Las horas fuera del horario de apertura no se muestran en el calendario (solo se ven las horas útiles).
- La pausa de mediodía (jornada partida) se muestra como un único bloque compacto en gris y no se puede seleccionar.
- Los días festivos aparecen en gris y no permiten asignar citas.
- Cada fisioterapeuta tiene un color asignado (configurable desde gestión de usuarios); las citas se muestran en el color de su fisio para diferenciarlas visualmente.
- Cada cita tiene un estado: pendiente, confirmada, cancelada o finalizada.
- Al finalizar una cita, su estado cambia a "Finalizada" y queda en solo lectura.
- Añadir notas a una cita (por ejemplo: "avisar un día antes por teléfono").
- Envío automático de recordatorio de cita al paciente 24 horas antes por email.
- Los emails enviados desde la app muestran el nombre de la clínica como remitente (configurado en CLINIC_NAME del .env).

### Lista de espera

- Accesible desde un botón en la vista del calendario (se abre como modal).
- Añadir un paciente a la lista de espera indicando:
  - Paciente (buscador con autocompletado)
  - Fisioterapeutas preferidos (selección múltiple, o ninguno = cualquiera)
  - Preferencia horaria: cualquier hora, solo mañanas, solo tardes, o franja concreta (hora desde - hora hasta)
  - Fecha: "Lo antes posible", un día concreto, o un rango de fechas
  - Prioridad: marcar como prioritario (se muestra antes en la lista)
  - Notas libres
- La lista se ordena por: fecha deseada más cercana → prioritarios primero → antigüedad de solicitud.
- Se registra la fecha y hora exacta en que se añadió a la lista.
- Los pacientes prioritarios se destacan visualmente con borde rojo.
- Al cancelar una cita, el sistema comprueba automáticamente si hay pacientes en lista de espera que encajen con el hueco liberado (fecha, hora, fisio). Si los hay, se muestra un aviso con opción de ver la lista de espera.
- Al crear una cita para un paciente que está en lista de espera, se ofrece eliminarlo automáticamente de la lista.

### Avisos internos

- Dejar avisos entre compañeros dentro de la aplicación (por ejemplo: recepción avisa al fisio de que un paciente llega 15 minutos tarde).
- Los avisos se reciben en tiempo real mediante WebSocket (sin necesidad de refrescar la página).
- Al recibir un aviso suena una notificación sonora y aparece un toast en pantalla.
- Los avisos no leídos se distinguen visualmente con borde grueso y texto en negrita.
- Se pueden eliminar avisos individualmente (con confirmación mediante modal).
- Se pueden marcar como leídos individualmente o todos a la vez.

### Facturación y pagos

- Registrar el pago de un paciente indicando el método (efectivo o bizum).
- Crear documentos de cobro eligiendo el tipo: factura, factura simplificada (recibo) o justificante. Por defecto justificante. Se asocia obligatoriamente a una cita o a un bono del paciente (las dos cosas que se cobran en la clínica).
- Editar documentos de cobro: botón de edición (lápiz) en la tabla. Modal con campos tipo documento, importe, método de pago y cita/bono asociado. Al guardar se regenera el PDF automáticamente.
- Al crear un documento de cobro se genera automáticamente el PDF y se guarda en el servidor.
- Botón "Ver PDF" para abrir el documento generado en una nueva pestaña.
- Botón "Enviar" para enviar el PDF por email al paciente. Si el paciente no tiene email configurado, se muestra un modal para introducirlo, guardarlo y enviar.
- En el selector de citas solo aparecen las que no tienen ya un documento de cobro asociado.
- En el selector de bonos se indica si están caducados.
- Si se selecciona un método de pago (efectivo o bizum) se marca como pagado automáticamente. Si se deja "Pendiente de pago" se marca como no pagado.
- Todo cobro pagado se registra automáticamente como ingreso en la contabilidad. Si se edita el importe o se desmarca como pagado, el ingreso se actualiza o elimina correspondientemente.
- Ver pacientes con pagos pendientes.
- Filtro de pagos pendientes en la lista de pacientes.

### Bonos de sesiones

- Gestionar bonos de sesiones desde la vista de bonos del paciente (`/patients/{id}/packs`), accesible desde la ficha del paciente.
- En la ficha del paciente se muestra un resumen del bono activo (sesiones consumidas/total, caducidad) como tabla clicable. Icono de advertencia rojo si tiene pago pendiente con modal para registrar pago. Botón "Crear bono" si no tiene bono activo.
- Crear bonos indicando número de sesiones, precio, caducidad, tipo de documento y método de pago (obligatoria).
- Editar bonos existentes (sesiones, precio, caducidad).
- Cancelar bonos: no se eliminan, se marcan como cancelados.
  - **Si el bono estaba pagado:** se elimina automáticamente su documento de cobro y se revierte el ingreso en contabilidad (devolución). Esto cubre el caso de que el paciente quiera recuperar su dinero o que se haya registrado erróneamente.
  - **Si el bono estaba pendiente de pago:** no se hace nada con la factura, simplemente se cancela el bono.
  - **IMPORTANTE:** Un bono NO se cancela porque el paciente deje de venir. En ese caso se deja sin tocar y cuando llegue su fecha de caducidad pasará automáticamente a estado "Caducado".
- Ver estado de bonos: activo (sesiones restantes), agotado, caducado o cancelado.
- Comprobación automática diaria (23:00): el sistema revisa si hay bonos cuya fecha de caducidad ha pasado y los marca como caducados.
- El consumo de sesiones se realiza al finalizar una cita desde el calendario.
- Al crear un bono se abre automáticamente el modal de facturación para registrar el cobro.

### Tratamientos y documentos

- Crear un tratamiento con ejercicios o recomendaciones para que el paciente haga en casa.
- Generar el consentimiento informado en PDF.
- Enviar documentos por email al paciente (facturas, justificantes, ejercicios, recomendaciones, consentimientos, etc.).

### Consentimientos informados

- Sección "Consentimientos" en la ficha del paciente con botón "+ Firmar".
- Un paciente puede firmar múltiples consentimientos (fisioterapia general, punción seca, suelo pélvico, etc.).
- Las plantillas son archivos `.docx` con marcadores `{{campo}}` ubicados en `app/static/docs/`.
- Al firmar se abre un modal con los campos que no se pueden rellenar automáticamente: fisioterapeuta, DNI fisio, unidad de fisioterapia, tutor/representante y observaciones.
- Los datos del paciente (nombre, DNI) y la fecha se rellenan automáticamente.
- Se genera un PDF firmado que se guarda en el directorio de documentos firmados.
- Cada consentimiento firmado se puede ver (PDF) o enviar por email al paciente.
- Lista de todos los consentimientos firmados del paciente con fecha y tipo de documento.

---

## Funciones exclusivas de administración

### Configuración de la clínica

- Configurar el horario de apertura para cada día de la semana (horario normal).
- Soporte para jornada partida: mañana y tarde con pausa intermedia.
- Las horas de pausa (cierre entre mañana y tarde) aparecen en gris en el calendario y no se pueden seleccionar.
- Crear horarios especiales para periodos concretos (ej: verano, Navidad, semanas específicas) que sobreescriben el horario normal durante esas fechas.
- Configurar días festivos: el día completo aparece en gris en el calendario y no se pueden asignar citas.
- El calendario solo muestra las horas comprendidas entre la apertura más temprana y el cierre más tardío configurados.
- Configurar la duración predeterminada de una cita (30, 45 o 60 minutos), que se aplica por defecto al crear una nueva cita.
- Configurar precio por defecto de sesión y precio por defecto de bono. Estos precios se precargan en los formularios de cobro pero se pueden modificar en cada caso.
- Configurar el horario personal de cada fisioterapeuta (entrada, salida, días libres). Si se intenta crear una cita fuera de su horario, se muestra un aviso pero se permite guardar si el usuario confirma.
- Cada fisioterapeuta tiene un color asignado (configurable con selector de color desde gestión de usuarios) que se usa en el calendario para diferenciar visualmente sus citas.

### Contabilidad

- Acceso protegido con contraseña (se pide la contraseña del usuario autenticado al entrar).
- Registrar, editar o eliminar ingresos.
- Registrar, editar o eliminar gastos.
- Ver el balance económico de un periodo de tiempo (mensual, bimensual, trimestral, anual o personalizado).

### Gestión de usuarios

- Dar de alta un nuevo usuario (recepción o fisioterapeuta).
- Al seleccionar el rol "Fisioterapeuta", el checkbox "Puede atender pacientes" se marca automáticamente.
- Editar los datos de un usuario.
- Desactivar un usuario (sin eliminarlo, para mantener el historial).

### Copia de seguridad

- Exportar la base de datos completa como archivo .db (descarga directa). Protegido con contraseña del usuario admin.
- Importar una copia de seguridad subiendo un archivo .db. Se eliminan todos los datos actuales y se reemplazan por los del archivo importado. Protegido con contraseña.
- Antes de restaurar se guarda automáticamente una copia del estado actual.
- Accesible desde Configuración > Backup (solo admin).

### Registro de actividad

- Ver un registro de quién ha hecho qué y cuándo dentro de la aplicación (por seguridad y protección de datos).

---

## Funciones para usuarios con permiso de fisioterapeuta (is_physio)

Cualquier usuario con el atributo `is_physio` activado puede acceder a estas funciones, independientemente de su rol administrativo (ADMIN, RECEPTION o PHYSIO).

### Historial clínico

- Ver el historial completo de sesiones de un paciente en formato tabla (fecha, observaciones, estado de pago). Accesible para todos los roles desde la ficha del paciente.
- La fecha y las observaciones son enlaces clicables que abren el detalle completo de la sesión.
- Las sesiones con pago pendiente muestran un enlace "Pendiente" que abre un modal para registrar el cobro (Efectivo o Bizum).
- Las sesiones se registran exclusivamente al finalizar una cita desde el calendario. La fecha y hora de la sesión es la de la cita, no la del momento de finalización. Cualquier rol puede finalizar citas.
- Generar justificante de asistencia en PDF desde el historial clínico (botón en cada sesión). Incluye fecha, hora y duración de la cita.
- Enviar justificante de asistencia por email al paciente directamente desde el historial clínico.
- Al finalizar una cita se abre un modal con: observaciones (opcional) y datos de pago (tipo documento, importe, método). Esto genera la sesión clínica y el documento de cobro.
- Botón ver: abre modal con todos los datos de la sesión.
- Botón editar: permite modificar solo las observaciones.

---

## Tipos de usuario

| Usuario | Descripción |
|---------|-------------|
| Administración | Acceso completo a todas las funciones. |
| Recepción | Funciones comunes (gestión de citas, pacientes, facturación). |
| Fisioterapeuta | Funciones comunes + historial clínico e informes. |

**Nota:** El acceso a funciones de fisioterapia (historial clínico, sesiones, informes) se controla mediante el atributo `is_physio`, independiente del rol. Un usuario con rol Administración o Recepción también puede tener acceso a estas funciones si tiene `is_physio` activado.
