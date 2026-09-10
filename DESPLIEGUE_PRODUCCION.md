# Despliegue en Producción (Raspberry Pi) — Santé

## Resumen

Sustituir la versión antigua completamente (código + BD), mantener el entorno virtual, montar USB para almacenamiento externo, configurar arranque automático.

---

## 1. Preparar el USB

Desde la Raspberry (o desde otro PC con Linux):

```bash
# Identificar el USB (normalmente /dev/sda1)
lsblk

# Formatear en ext4 (BORRA TODO el contenido del USB)
sudo umount /dev/sda1
sudo mkfs.ext4 -L SANTE_USB /dev/sda1

# Crear punto de montaje
sudo mkdir -p /media/usb

# Montar temporalmente para verificar
sudo mount /dev/sda1 /media/usb
ls /media/usb

# Desmontar (lo montaremos definitivamente después)
sudo umount /media/usb
```

---

## 2. Configurar montaje automático del USB

```bash
# Obtener UUID del USB
sudo blkid /dev/sda1
```

Apunta el UUID (ej: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

```bash
# Editar fstab para montaje automático al arrancar
sudo nano /etc/fstab
```

Añadir al final:

```
UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx /media/usb ext4 defaults,noatime,nofail 0 2
```

> `nofail` evita que la Raspberry no arranque si el USB no está conectado.

```bash
# Montar ahora sin reiniciar
sudo mount -a

# Verificar
df -h | grep usb
```

---

## 3. Crear estructura de carpetas en el USB

```bash
sudo mkdir -p /media/usb/documentos_firmados
sudo mkdir -p /media/usb/facturas
sudo mkdir -p /media/usb/pacientes
sudo mkdir -p /media/usb/backups
sudo mkdir -p /media/usb/logs

# Dar permisos al usuario de la app
sudo chown -R pi:pi /media/usb
```

---

## 4. Copiar la nueva versión de la app

### Opción A: Desde USB (copiar archivos)

```bash
# Montar USB con el código (si lo traes en otro USB)
sudo mkdir -p /media/usb_code
sudo mount /dev/sdb1 /media/usb_code

# Parar la app
sudo systemctl stop sante

# Borrar código antiguo (mantener entorno virtual)
cd /home/pi/sante
rm -rf app/ tests/ templates/ static/ *.py *.md .env requirements.txt

# Copiar código nuevo
cp -r /media/usb_code/sante/* /home/pi/sante/

# Desmontar USB de código
sudo umount /media/usb_code
```

### Opción B: Desde SCP (red local)

```bash
# Desde tu PC Windows (en cmd/PowerShell):
scp -r C:\PoC\sante\* pi@<IP_RASPBERRY>:/home/pi/sante/
```

---

## 5. Instalar dependencias nuevas

```bash
cd /home/pi/sante
source venv/bin/activate
pip install -r requirements.txt
```

> **Nota**: `docx2pdf` en Linux usa LibreOffice. Si no está instalado:
> ```bash
> sudo apt install libreoffice -y
> ```

---

## 6. Configurar .env

```bash
nano /home/pi/sante/.env
```

Contenido para producción:

```env
SECRET_KEY=una-clave-secreta-larga-y-aleatoria
SMTP_HOST=smtp.ionos.es
SMTP_PORT=587
SMTP_USER=info@centrosante.es
SMTP_PASSWORD=<contraseña-email>
SMTP_FROM=info@centrosante.es
CLINIC_NAME=Centro Santé Fisioterapia y Osteopatía
CLINIC_PHONE=636554300
CLINIC_ADDRESS=Calle Valle de la Fuente, 25, Valverde del Camino
CLINIC_CIF=44241271N
SIGNED_DOCS_PATH=/media/usb/documentos_firmados
INVOICES_PATH=/media/usb/facturas
PATIENT_DOCS_PATH=/media/usb/pacientes
LOG_PATH=/media/usb/logs/errors.log
AUTO_BACKUP_PATH=/media/usb/backups
```

---

## 7. Crear carpeta de logs local (por si el USB no está)

```bash
mkdir -p /home/pi/sante/app/logs
```

---

## 8. Verificar que arranca

```bash
cd /home/pi/sante
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Accede desde el navegador a `http://<IP_RASPBERRY>:8000` y verifica que funciona. Ctrl+C para parar.

---

## 9. Configurar servicio systemd (arranque automático)

Verificar si ya existe:

```bash
sudo systemctl status sante
```

Si existe, actualizar el archivo:

```bash
sudo nano /etc/systemd/system/sante.service
```

Contenido:

```ini
[Unit]
Description=Santé Fisioterapia App
After=network.target
After=media-usb.mount
Wants=media-usb.mount

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sante
ExecStart=/home/pi/sante/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PATH=/home/pi/sante/venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
```

Aplicar cambios:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sante
sudo systemctl start sante
```

Verificar:

```bash
sudo systemctl status sante
```

---

## 10. Verificar funcionamiento completo

- [ ] Acceder a `http://<IP_RASPBERRY>:8000`
- [ ] Login con tu usuario
- [ ] Crear un paciente de prueba
- [ ] Firmar un consentimiento → verificar que el PDF se crea en `/media/usb/documentos_firmados/`
- [ ] Verificar que los logs se escriben en `/media/usb/logs/errors.log`
- [ ] Probar el botón "Apagar" en Configuración > Backup

---

## 11. Apagar de forma segura

Desde la app: **Configuración > Backup > Apagar**

O desde terminal:

```bash
sudo shutdown -h now
```

**NUNCA desenchufar sin apagar.** Esperar a que el LED verde deje de parpadear.

---

## Solución de problemas

### La app no arranca

```bash
sudo journalctl -u sante -n 50 --no-pager
```

### El USB no se monta

```bash
sudo mount -a
# Si falla, verificar UUID:
sudo blkid
# Comparar con /etc/fstab
```

### Permisos denegados en USB

```bash
sudo chown -R pi:pi /media/usb
```

### LibreOffice no convierte (consentimientos)

```bash
sudo apt install libreoffice -y
# Verificar:
libreoffice --headless --convert-to pdf /tmp/test.docx
```

### Regenerar PDFs en blanco (si se añaden plantillas nuevas)

```bash
cd /home/pi/sante
source venv/bin/activate
python -c "from app.consent_generator import generate_blank_pdfs; generate_blank_pdfs()"
```

---

## Estructura final

```
/home/pi/sante/          ← Código de la app + BD (sante.db)
/media/usb/
├── documentos_firmados/ ← PDFs de consentimientos firmados
├── facturas/            ← PDFs de facturas/justificantes
├── pacientes/           ← Documentos adjuntos de pacientes
├── backups/             ← Backup diario + mensuales
│   ├── sante_diaria.db
│   ├── sante_mensual_202605.db
│   └── ...
└── logs/
    └── errors.log
```
