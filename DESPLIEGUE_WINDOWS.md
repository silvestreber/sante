# Despliegue en Windows — Santé

---

## Requisitos previos

- **Python 3.10+** instalado ([python.org](https://www.python.org/downloads/))
  - Durante la instalación, marcar "Add Python to PATH"
- **Git** (opcional, si clonas desde repositorio)

---

## Paso a paso

### 1. Obtener el proyecto

Si tienes el código en una carpeta (ej: `C:\PoC\sante`), navega a ella:

```cmd
cd C:\PoC\sante
```

Si lo clonas desde un repositorio:

```cmd
git clone <url-del-repositorio> C:\PoC\sante
cd C:\PoC\sante
```

### 2. Crear entorno virtual

```cmd
python -m venv venv
```

### 3. Activar entorno virtual

```cmd
venv\Scripts\activate
```

Verás `(venv)` al inicio del prompt.

### 4. Instalar dependencias

```cmd
pip install -r requirements.txt
```

> **Nota**: La app usa `docx2pdf` para generar consentimientos firmados. En Windows necesita Microsoft Word instalado. En Linux (Raspberry Pi) necesita LibreOffice: `sudo apt install libreoffice`.

### 5. Configurar variables de entorno

Edita el archivo `.env` en la raíz del proyecto con los datos reales de tu clínica:

```
SECRET_KEY=una-clave-secreta-larga-y-aleatoria
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu-email@gmail.com
CLINIC_NAME=Clínica SANTÉ
CLINIC_PHONE=600000000
CLINIC_ADDRESS=Tu dirección
CLINIC_CIF=<NIF-autónoma>
UPLOADS_PATH=./uploads
BACKUPS_PATH=./backups
SIGNED_DOCS_PATH=C:/PoC/documentos_firmados
```

> **Nota sobre Gmail:** Necesitas generar una "Contraseña de aplicación" en tu cuenta de Google (Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones).

### 6. Crear carpetas necesarias

```cmd
mkdir uploads
mkdir backups
mkdir app\logs
mkdir pdf_templates
mkdir logos
mkdir C:\PoC\documentos_firmados
```

> Las carpetas `logos/` y `pdf_templates/` ya vienen con el proyecto si lo clonas. Solo créalas si partes de cero.
> La carpeta `documentos_firmados` almacena los consentimientos firmados por los pacientes.

### 7. Ejecutar tests (opcional)

```cmd
python -m pytest tests/ -v
```

Deben pasar los 49 tests.

### 8. Inicializar la base de datos y datos de prueba

```cmd
python seed.py
```

Esto crea la base de datos `sante.db` con:
- Usuarios de prueba (maria, angel, lucia, patricia)
- 50 pacientes de ejemplo

### 9. Arrancar la aplicación

```cmd
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 10. Acceder a la aplicación

Abre el navegador en: **http://localhost:8000**

Credenciales de prueba:

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| maria | maria123 | Admin + Fisio |
| angel | angel123 | Fisio |
| lucia | lucia123 | Fisio |
| patricia | patricia123 | Recepción |

### 11. Configurar horarios

Una vez dentro con el usuario `maria` (admin):
1. Abre el menú hamburguesa → **Configuración**
2. Tab **Horario semanal**: configura apertura/cierre de cada día
3. Tab **Festivos**: añade días festivos
4. Tab **Horarios fisios**: configura el horario de cada fisioterapeuta
5. Tab **General**: establece la duración predeterminada de cita

---

## Arranque rápido (después de la primera vez)

```cmd
cd C:\PoC\sante
venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Acceso desde otros dispositivos en la red local

Si quieres acceder desde el móvil u otro PC en la misma red WiFi:

1. Averigua la IP de tu máquina:
   ```cmd
   ipconfig
   ```
   Busca la dirección IPv4 (ej: `192.168.1.50`)

2. Accede desde el otro dispositivo a: `http://192.168.1.50:8000`

---

## Solución de problemas

### "No se reconoce python como comando"
- Reinstala Python marcando "Add Python to PATH"
- O usa la ruta completa: `C:\Users\TuUsuario\AppData\Local\Programs\Python\Python3XX\python.exe`

### "El puerto 8000 ya está en uso"
```cmd
netstat -ano | findstr :8000
taskkill /PID <numero> /F
```

### "Error de base de datos"
Elimina `sante.db` y vuelve a ejecutar `python seed.py`

### La app no arranca tras cambios en modelos
Si has modificado modelos de la base de datos:
```cmd
del sante.db
python seed.py
```

---

## Crear acceso directo para arrancar

Crea un archivo `arrancar.bat` en la raíz del proyecto:

```bat
@echo off
cd /d C:\PoC\sante
call venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
```

Haz doble clic en `arrancar.bat` para iniciar la app.


---

## Cambiar el email a IONOS (producción)

Cuando el cliente proporcione los datos de su cuenta de email en IONOS, hay que cambiar las variables SMTP en el archivo `.env`:

### Datos necesarios del cliente

- Email de IONOS (ej: `info@clinicasante.es`)
- Contraseña del email

### Configuración

Edita el archivo `.env` y cambia estas líneas:

```
SMTP_HOST=smtp.ionos.es
SMTP_PORT=587
SMTP_USER=info@clinicasante.es
SMTP_PASSWORD=la-contraseña-del-email
SMTP_FROM=info@clinicasante.es
```

### Datos SMTP de IONOS

| Parámetro | Valor |
|-----------|-------|
| Servidor SMTP | `smtp.ionos.es` |
| Puerto | `587` (STARTTLS) |
| Seguridad | STARTTLS |
| Autenticación | Email completo + contraseña |

### Pasos

1. Detener la aplicación (Ctrl+C en la terminal)
2. Editar `.env` con los datos de arriba
3. Reiniciar la aplicación:
   ```cmd
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. Probar enviando un documento por email desde la app a una dirección conocida

### Notas

- No se necesita "contraseña de aplicación" como en Gmail. Se usa la contraseña normal del buzón de IONOS.
- Si IONOS usa puerto 465 con SSL directo en vez de 587 con STARTTLS, habría que modificar `email_service.py` para usar `smtplib.SMTP_SSL` en vez de `smtplib.SMTP` + `starttls()`. Consultar con el soporte de IONOS si hay problemas de conexión.
- El email configurado será el remitente de: recordatorios de cita, facturas, justificantes, tratamientos y consentimientos.
- El nombre que ve el destinatario como remitente es el valor de `CLINIC_NAME` en el `.env`. Se codifica automáticamente con RFC 2047 para compatibilidad con IONOS y caracteres especiales (acentos, eñes, etc.).

### Configuración actual (desarrollo)

Mientras no se tenga la cuenta de IONOS, se usa una cuenta de Gmail:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<email>@gmail.com
SMTP_PASSWORD=<app-password>
SMTP_FROM=<email>@gmail.com
```
