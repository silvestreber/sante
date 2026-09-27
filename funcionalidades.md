# Funcionalidades de la aplicación de gestión de clínica

Documento de referencia de todo lo que hace la aplicación. Actualizado al estado actual.

---

## Funciones comunes (todos los usuarios)

### Sesión y autenticación

- El inicio de sesión pide usuario y contraseña. En la pantalla de login hay un botón (icono de ojo) para mostrar u ocultar la contraseña mientras se escribe.
- La sesión se mantiene activa mientras se usa la aplicación. El acceso caduca automáticamente tras **30 minutos de inactividad** (sin clics, teclado, scroll ni toques en pantalla).
- Mientras el usuario trabaja, la sesión se renueva sola de forma transparente; no hace falta volver a iniciar sesión cada cierto tiempo. Las tareas automáticas de fondo (como la comprobación de avisos) no cuentan como actividad, así que 30 minutos parado sí cierran la sesión.
- Si la sesión caduca, al intentar cualquier acción se redirige automáticamente a la pantalla de login.

### Pacientes

- Registrar un nuevo paciente mediante un formulario con sus datos personales (nombre, apellidos, teléfono, email, dirección, fecha de nacimiento, DNI/NIE, notas).
- Ver la lista completa de pacientes, con **búsqueda flexible** por nombre, apellidos o teléfono: se puede escribir cualquier combinación de palabras en cualquier orden (por ejemplo "Pérez Castilla", "Francisco Castilla" o solo "isco") y encontrará al paciente. La búsqueda **no distingue mayúsculas/minúsculas ni tildes** (buscar "perez" encuentra "Pérez").
- **Pacientes sin ficha (provisionales):** un paciente nuevo puede darse de alta con datos mínimos (nombre, apellidos, teléfono y email opcional) directamente al crear una cita, sin necesidad de rellenar la ficha completa. Estos pacientes se marcan como "sin ficha" y su ficha clínica se completa más adelante, cuando acuden a la consulta (ver "Completar ficha").
- **Notas del paciente:** la ficha incluye un campo de notas libres para anotaciones generales sobre el paciente, editable desde el formulario y visible en la ficha.
- Desactivar pacientes (borrado lógico): el paciente deja de aparecer en la lista pero se conservan todos sus datos, historial, citas y facturas. Solo disponible para admin y recepción.
- Ver pacientes no activos mediante un toggle en la lista, desde donde se pueden reactivar.
- La ficha del paciente se divide en dos vistas con un **toggle "Ficha / Historial"** en la parte superior:
  - **Ficha:** datos del paciente (incluidas las notas), alergias/contraindicaciones destacadas (si las hay), resumen del bono activo y botón "Editar".
  - **Historial:** historial clínico de sesiones (ver más abajo).
- **Completar ficha:** si el paciente es provisional (dado de alta solo para una cita), la ficha muestra un aviso con un botón "Completar ficha" que abre el formulario para rellenar sus datos clínicos. Al guardar la ficha completa, el paciente deja de ser provisional. Este mismo aviso aparece también en la cita del calendario.
- En la cabecera de la ficha hay **botones directos** de acceso a: Tratamientos, Pagos y Documentos (más el botón "Volver").
- Si el paciente tiene algún pago pendiente, aparece un **icono de aviso rojo junto a su nombre**. El aviso se actualiza en el momento al registrar un pago, sin recargar la página.
- Adjuntar documentos a la ficha del paciente (radiografías, informes externos, fotos de evolución, etc.), con descripción obligatoria. Se pueden ver directamente en el navegador. Accesible desde el botón "Documentos".

### Calendario y citas

- Al iniciar sesión, la vista principal es el calendario.
- Al entrar tras el login se muestra un modal con los avisos sin leer, solo si hay alguno pendiente.
- Vistas de mes, semana y día. En pantallas pequeñas (móvil) la cabecera del calendario se adapta automáticamente.
- Los días de la semana siempre cerrados y las horas fuera del horario de apertura no se muestran. La pausa de mediodía (jornada partida) aparece como un bloque compacto en gris y no se puede seleccionar. Los días festivos aparecen en gris y no permiten citas.
- Cada fisioterapeuta tiene un color asignado; sus citas se muestran en ese color. Las citas simultáneas de distintos fisios se muestran lado a lado, sin superposición.
- Las citas **pendientes** se muestran con opacidad reducida. Las citas **finalizadas** se distinguen con un patrón de rayas diagonales y un "✓" delante del nombre del paciente.
- Botón "Nueva cita" junto al título, y también se puede crear haciendo clic en el calendario:
  - En vista de semana o día, el clic en una franja horaria abre el modal en esa hora.
  - En vista de mes, el clic en un día abre el modal con la hora de apertura de ese día.
- Filtros del calendario: por ubicación (clínica/domicilio) y por estado (pendientes/confirmadas). Si el usuario es fisioterapeuta, por defecto ve solo sus citas.

#### Crear y editar una cita

El modal de cita funciona así:

- **Paciente:** buscador con autocompletado (búsqueda flexible por nombre/apellidos/teléfono, sin distinguir mayúsculas ni tildes; muestra todos los resultados con scroll si hay muchos).
  - **Paciente nuevo (sin ficha):** junto al buscador hay un botón que despliega un mini-formulario (nombre, apellidos, teléfono y email opcional). Al guardar la cita, el paciente provisional se crea automáticamente y queda asignado a la cita, sin pasos adicionales.
- **Fisioterapeuta:** si el usuario es fisio, se preselecciona a sí mismo.
- **Día:** selector de fecha.
- **Hora:** al elegir día y fisioterapeuta, aparece un desplegable con **las horas disponibles** de ese fisio para ese día. Las horas se calculan automáticamente a partir del horario del fisio (mañana y tarde, respetando la pausa del mediodía) en intervalos según la **duración configurada**. Las horas ya ocupadas aparecen deshabilitadas y marcadas como "(ocupada)". Si se cambia el fisioterapeuta, el desplegable se recalcula con su agenda.
- **La duración ya no se elige**: se aplica automáticamente la duración predeterminada configurada.
- **Lugar:** clínica o domicilio.
- **Notas** de la cita.
- El modal se cierra con la **"X"** de la esquina superior derecha o haciendo clic fuera del modal.
- El calendario impide solapar citas del mismo fisioterapeuta. El backend valida además que no se creen citas fuera del horario de apertura ni en festivos (con opción de "Guardar de todas formas" para excepciones). Si la fecha/hora es anterior a la actual, se pide confirmación.
- Al editar una cita se muestra su estado actual como texto. Los botones disponibles dependen del estado:
  - **Confirmar cita** (solo si está pendiente).
  - **Finalizar** (solo si está confirmada y aún no tiene sesión registrada).
  - **Cancelar cita**.
  - **Guardar cambios**.
  - **Enviar recordatorio** por WhatsApp.
- Si la cita está **finalizada**, queda en solo lectura: el nombre del paciente pasa a ser un enlace a su ficha, y solo se muestran las acciones de justificante de asistencia (ver más abajo). No se muestran "Enviar recordatorio" ni "Cancelar cita".
- Crear **citas recurrentes** (ej.: "todos los martes y jueves durante 4 semanas"). Las que solaparían con citas existentes se omiten.
- Si se cancela una cita, su hueco vuelve a quedar disponible y seleccionable.
- Envío automático de recordatorio de cita al paciente 24 horas antes por email. Los emails muestran el nombre de la clínica como remitente.

#### Finalizar una cita

Al finalizar una cita se abre un modal con:

- **Seguimiento** (observaciones de la sesión, opcional). Esto genera la sesión clínica en el historial.
- **Tipo de documento** (justificante, factura o factura simplificada).
- **Importe** (obligatorio; se precarga con el precio de sesión configurado y se puede modificar).
- **Método de pago:** pendiente de pago, efectivo, bizum o **bono**.
- Si el paciente tiene un bono activo con sesiones disponibles, aparece la opción "Consumir sesión del bono". Al marcarla, el método pasa automáticamente a "Bono" y el importe en euros pasa a 0; al desmarcarla vuelve a "Pendiente" y reaparece el importe. La sincronización funciona en ambos sentidos (marcar el bono en el desplegable marca el check y viceversa).

**Regla importante:** el documento de cobro **solo se genera si hay pago** (efectivo, bizum o bono). Si la cita se deja **pendiente de pago**, no se crea ningún documento; el importe queda guardado en la cita y el documento se generará más adelante al registrar el pago desde la vista de Pagos.

- El importe de la sesión queda guardado en la propia cita, aunque el pago quede pendiente.
- El pago con bono consume una sesión del bono. Un paciente con bono al que no se le marca el consumo se cobra como un paciente normal.

### Facturación y pagos (vista "Pagos" del paciente)

- La vista tiene un **toggle "Cita / Bono"** para elegir qué se está cobrando.
- Si no hay citas (o bonos) pendientes de pago, se muestra un mensaje indicándolo y no aparece el formulario.
- Cuando hay pendientes, el formulario tiene, en este orden:
  1. **Desplegable** con las citas (o bonos) pendientes de pago.
  2. **Importe**, con el símbolo €, autorrellenado según la cita/bono elegido (editable).
  3. **Método de pago** (efectivo o bizum; aquí no existe la opción "pendiente", porque registrar el pago implica que se ha cobrado).
  4. **Tipo de documento** (justificante, factura o factura simplificada).
  5. Botón **Registrar**.
- El pago con sesión de bono solo se hace al finalizar la cita. Si una cita se dejó pendiente, desde aquí solo se puede cobrar con dinero.
- Al registrar el pago se genera el documento PDF, se guarda y se registra el ingreso en contabilidad.
- **Historial de documentos:** tabla con fecha de cobro, tipo, cita/bono asociado, importe, método, estado (pagado/pendiente) y acciones. La fila completa es clicable para **ver el PDF**. Acciones por fila: editar, registrar pago (si está pendiente), enviar por email y eliminar.
- **Editar un documento:** se puede cambiar el tipo, importe, método de pago y la cita/bono asociado. Si se cambia el tipo de documento (por ejemplo de justificante a factura), el documento se regenera desde cero: se borra el PDF anterior, se renumera con el prefijo correspondiente y se genera el nuevo PDF.
- **Eliminar un documento:** se borra por completo (el PDF, el registro y el ingreso asociado en contabilidad). La cita o bono asociado queda libre de nuevo, como si nunca se hubiera cobrado.
- **Enviar por email:** envía el PDF al paciente. Si no tiene email registrado, se pide introducirlo.
- Numeración de documentos por año y tipo: Justificante `J-AAAA-NNNN`, Factura `F-AAAA-NNNN`, Factura simplificada `FS-AAAA-NNNN`.
- Métodos de pago disponibles: efectivo y bizum.
- Filtro de pagos pendientes en la lista de pacientes, y aviso de pagos pendientes en la ficha.

### Bonos de sesiones

- Gestión de bonos desde la vista de bonos del paciente y desde el resumen de la ficha.
- En la ficha se muestra el bono activo (sesiones consumidas/total y caducidad). Si no tiene, aparece un botón "Crear bono".
- **Crear bono:** por defecto **10 sesiones** y **caducidad a 6 meses** (ambos editables), más precio, tipo de documento y método de pago.
- Al igual que las citas, el documento de cobro del bono **solo se crea si hay pago**. Si se deja pendiente, no se genera documento (se hará al registrar el pago del bono).
- Editar bonos (sesiones, precio, caducidad). Si se cambia el precio de un bono ya pagado, se regenera su documento y se ajusta el ingreso.
- **Cancelar bono:** no se elimina, se marca como cancelado.
  - Si estaba pagado, se elimina su documento de cobro y se revierte el ingreso (devolución).
  - Si estaba pendiente, simplemente se cancela.
  - Un bono NO se cancela porque el paciente deje de venir: en ese caso se deja y pasará a "Caducado" al llegar su fecha.
- Estados del bono: activo (con sesiones restantes), agotado, caducado o cancelado.
- El consumo de sesiones se realiza al finalizar una cita marcando "Consumir sesión del bono".

### Tratamientos y documentos

- Crear tratamientos con ejercicios o recomendaciones para el paciente, y generarlos en PDF.
- Enviar documentos por email al paciente (facturas, justificantes, ejercicios, consentimientos, etc.).
- **Todos los PDF generados por la aplicación** (facturas, justificantes, tratamientos, justificante de asistencia) llevan el logo de la clínica como marca de agua tenue de fondo.
- Además, estos documentos incluyen un **pie de página institucional** con el logo de la clínica y los datos del centro (colegiada y nº de colegiado, dirección, teléfono, email y NICA).

### Consentimientos informados

- Un paciente puede firmar múltiples consentimientos (fisioterapia general, punción seca, suelo pélvico, información de tratamiento de datos, etc.).
- Al firmar se abre un modal con los datos que no se rellenan solos. En el consentimiento de fisioterapia general, los campos de fisioterapeuta, DNI del fisio y unidad de fisioterapia son **opcionales**: si se dejan vacíos, el documento sale con líneas para rellenar a mano.
- Los datos del paciente (nombre, DNI) y la fecha se rellenan automáticamente.
- La firma se dibuja en pantalla (con el dedo en tablet/móvil o con el ratón). La firma del paciente es obligatoria; la del tutor/representante solo si se indican sus datos.
- Se genera un PDF firmado que se guarda en los documentos del paciente. Cada consentimiento firmado se puede ver o enviar por email. También existe la opción de documento de revocación.

### Justificantes de asistencia

- Desde una cita **finalizada** (en el calendario) y desde el historial clínico se puede **ver** o **enviar por email** un justificante de asistencia en PDF.
- El justificante recoge los datos de la cita: paciente, fecha, hora y duración.
- El justificante lo firma el fisioterapeuta que atendió la cita: si ese fisio tiene una firma registrada, se estampa automáticamente en el documento.

---

## Funciones exclusivas de administración

### Configuración de la clínica

- Configurar el horario de apertura para cada día de la semana, con soporte de jornada partida (mañana y tarde con pausa).
- Crear horarios especiales para periodos concretos (verano, Navidad, etc.) que sobreescriben el horario normal durante esas fechas.
- Configurar días festivos.
- Configurar el **horario personal de cada fisioterapeuta** (mañana, tarde y días libres). Es lo que determina las horas disponibles al crear una cita para ese fisio.
- Registrar **ausencias y vacaciones** de los fisioterapeutas (rango de fechas, opcionalmente franja horaria).
- Configurar la **duración predeterminada de una cita**, introduciéndola como número de minutos (campo numérico libre).
- Configurar el precio por defecto de sesión y de bono (se precargan en los formularios de cobro, modificables en cada caso).
- Configurar el mensaje del recordatorio de WhatsApp.
- Asignar un color a cada fisioterapeuta (usado en el calendario).
- Importar pacientes desde Excel y exportar la facturación para la gestoría en Excel.

### Contabilidad

- Acceso protegido con la contraseña del usuario autenticado.
- Registrar, editar o eliminar ingresos y gastos.
- Ver el balance económico de un periodo (mensual, trimestral, anual o personalizado).
- Los cobros a pacientes se registran automáticamente como ingresos. Al eliminar o modificar un documento de cobro, el ingreso se actualiza o elimina en consecuencia.

### Gestión de usuarios

- Dar de alta usuarios (recepción o fisioterapeuta). Al elegir el rol "Fisioterapeuta" se marca automáticamente "Puede atender pacientes".
- Editar los datos de un usuario y su color de calendario.
- **Registrar la firma del fisioterapeuta** dibujándola en pantalla (mismo componente que los consentimientos). Esa firma se estampa en los justificantes de asistencia de sus citas.
- Desactivar/reactivar un usuario (sin eliminarlo, para mantener el historial). No es posible desactivarse a uno mismo.

### Copia de seguridad

- Exportar la base de datos completa como archivo `.db` (protegido con contraseña del admin).
- Importar una copia de seguridad; antes de restaurar se guarda automáticamente una copia del estado actual.
- Accesible desde Configuración (solo admin).

### Registro de actividad (auditoría)

- Registro de quién ha hecho qué y cuándo (crear, editar, eliminar, cancelar, etc.), con filtros por usuario, acción, entidad y fechas.

---

## Funciones para usuarios con permiso de fisioterapeuta (is_physio)

Cualquier usuario con el atributo `is_physio` activado puede acceder a estas funciones, independientemente de su rol (ADMIN, RECEPTION o PHYSIO).

### Historial clínico

- Ver el historial de sesiones del paciente en tabla (fecha, seguimiento, estado de pago), dentro de la pestaña "Historial" de la ficha.
- Ordenar por fecha ascendente o descendente (por defecto, las más recientes primero) y buscar por fecha u observaciones.
- Cada fila abre el detalle de la sesión. Las sesiones con pago pendiente muestran un enlace "Pendiente" para registrar el cobro. El pago con bono se muestra como tal.
- Las sesiones se registran normalmente al finalizar una cita desde el calendario. La fecha de la sesión es la de la cita. Cualquier rol puede finalizar citas.
- **Añadir sesión manualmente:** en la cabecera del historial hay un botón "Añadir sesión" para registrar sesiones anteriores o realizadas fuera de la clínica (sin cita asociada). Se indica fecha, hora, fisioterapeuta (opcional) y seguimiento. Estas sesiones se marcan con una etiqueta "Manual", no tienen estado de pago ni generan cobro.
- Desde cada sesión se puede editar el seguimiento, y generar o enviar por email el justificante de asistencia. **Las sesiones manuales no permiten justificante de asistencia** (no se realizaron en la clínica): esos botones no aparecen y el servidor también lo impide.

---

## Avisos internos

- Dejar avisos entre compañeros dentro de la aplicación (por ejemplo, recepción avisa al fisio de que un paciente llega tarde).
- Los avisos se reciben en tiempo real (sin refrescar la página), con sonido y aviso en pantalla.
- Los no leídos se distinguen visualmente. Se pueden marcar como leídos (individualmente o todos) y eliminar.

---

## Lista de espera

- Accesible desde un botón en el calendario.
- Añadir un paciente indicando: fisioterapeutas preferidos (o cualquiera), preferencia horaria (cualquier hora, mañanas, tardes o franja concreta), fecha (lo antes posible, un día concreto o un rango), prioridad y notas.
- La lista se ordena por fecha deseada, prioridad y antigüedad de la solicitud. Los prioritarios se destacan.
- Al cancelar una cita, el sistema comprueba si hay pacientes en lista de espera que encajen con el hueco liberado.
- Al crear una cita para un paciente que está en lista de espera, se ofrece quitarlo de la lista.

---

## Tipos de usuario

| Usuario | Descripción |
|---------|-------------|
| Administración | Acceso completo a todas las funciones. |
| Recepción | Funciones comunes (citas, pacientes, facturación). |
| Fisioterapeuta | Funciones comunes + historial clínico y sesiones. |

**Nota:** el acceso a las funciones de fisioterapia se controla con el atributo `is_physio`, independiente del rol. Un usuario de Administración o Recepción también puede tenerlas si tiene `is_physio` activado.
