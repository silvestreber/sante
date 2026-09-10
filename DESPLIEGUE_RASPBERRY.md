# Despliegue en Raspberry Pi — Santé (Producción)

---

## ⚠️ Datos de acceso reales de la Raspberry de producción

> **IMPORTANTE — leer antes de intentar entrar.** Estos son los datos reales
> de la Raspberry en producción, que NO coinciden con los valores de ejemplo
> (`sante` / `sante-server`) que aparecen más abajo en la guía.

| Elemento | Valor real en producción |
|----------|--------------------------|
| Usuario del sistema | `silver` |
| Prompt de login que aparece | `raspberrypi login:` (hostname por defecto, `raspberrypi`) |
| IP en la red de casa (traslado) | `192.168.0.100` |
| Acceso local | Teclado + monitor (SO solo consola, sin escritorio) |
| Acceso remoto | SSH activo: `ssh silver@<IP>` |
| SO | Raspberry Pi OS Lite basado en **Debian 13 (trixie)** |

> **La contraseña se definió al flashear con Raspberry Pi Imager.** Guárdala en
> un gestor de contraseñas. Si se pierde, se recupera montando la microSD en un
> PC y reseteando la contraseña (sin perder datos).

> **Rutas reales verificadas en producción** (`whoami`, `pwd`, `systemctl cat sante`):
>
> | Elemento | Ruta / valor real |
> |----------|-------------------|
> | Home del usuario | `/home/silver` |
> | Proyecto | `/home/silver/sante` |
> | Entorno virtual (venv) | `/home/silver/venv` (¡FUERA del proyecto!) |
> | Ejecutable Python del venv | `/home/silver/venv/bin/python` |
> | Servicio systemd | `sante.service` con `User=silver` |
> | Dependencia de montaje USB | `media-usb.mount` (el servicio la requiere para arrancar) |
>
> Los ejemplos de más abajo en esta guía usan `sante` y `venv` dentro del
> proyecto como **placeholders**; los valores reales son los de esta tabla.

---

## Requisitos de hardware

- **Raspberry Pi 4** (2 GB RAM mínimo, recomendado 4 GB)
- Tarjeta microSD de 32 GB (clase 10 o superior)
- USB externo para backups (formateado en ext4 o NTFS)
- Conexión Ethernet (recomendado) o WiFi estable
- Fuente de alimentación oficial (5V 3A)

---

## Requisitos de software

- **Raspberry Pi OS Lite** (64-bit, basado en Debian Bookworm)
- Python 3.11+ (incluido en Raspberry Pi OS Bookworm)
- Git

---

## Paso a paso

### 1. Preparar el sistema operativo

Flashear Raspberry Pi OS Lite con [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

En la configuración avanzada del Imager:
- Activar SSH
- Configurar usuario (ej: `sante`) y contraseña
- Configurar WiFi si no usas Ethernet
- Establecer hostname (ej: `sante-server`)

### 2. Conectar por SSH

```bash
ssh sante@sante-server.local
```

### 3. Actualizar el sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git
```

### 4. Obtener el proyecto

```bash
cd /home/sante
git clone <url-del-repositorio> sante
cd sante
```

O copiar la carpeta del proyecto vía SCP:

```bash
scp -r C:\PoC\sante\ sante@sante-server.local:/home/sante/sante
```

### 5. Crear entorno virtual

> **En producción el venv está en `/home/silver/venv` (fuera del proyecto).**
> Reproducir ese esquema:

```bash
cd /home/silver
python3 -m venv venv
source venv/bin/activate
cd sante
```

### 6. Instalar dependencias

```bash
pip install -r requirements.txt
```

> En Raspberry Pi la compilación de `bcrypt` puede tardar unos minutos. Si falla, instalar dependencias de compilación:
> ```bash
> sudo apt install -y build-essential libffi-dev python3-dev
> ```

### 7. Crear carpetas necesarias

```bash
mkdir -p uploads backups app/logs pdf_templates
```

### 8. Configurar variables de entorno

```bash
nano .env
```

Contenido para producción:

```
SECRET_KEY=<clave-secreta-larga-y-aleatoria>
SMTP_HOST=smtp.ionos.es
SMTP_PORT=587
SMTP_USER=info@clinicasante.es
SMTP_PASSWORD=<contraseña-email-ionos>
SMTP_FROM=info@clinicasante.es
CLINIC_NAME=Santé Fisioterapia
CLINIC_PHONE=<teléfono-clínica>
CLINIC_ADDRESS=<dirección-clínica>
CLINIC_CIF=<NIF-autónoma>
UPLOADS_PATH=./uploads
BACKUPS_PATH=./backups
```

> Generar una SECRET_KEY segura: `python3 -c "import secrets; print(secrets.token_hex(32))"`

### 9. Inicializar la base de datos

```bash
python seed.py
```

> **IMPORTANTE:** En producción, tras el primer arranque, cambiar las contraseñas de los usuarios desde la app (Configuración > Usuarios).

### 10. Verificar que funciona

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Acceder desde otro dispositivo en la red: `http://sante-server.local:8000`

Detener con `Ctrl+C` una vez verificado.

---

## Configurar como servicio (systemd)

Para que la app arranque automáticamente al encender la Raspberry Pi:

### 1. Crear el servicio

```bash
sudo nano /etc/systemd/system/sante.service
```

Contenido (**configuración real de producción**):

```ini
[Unit]
Description=Santé Fisioterapia
After=network.target
After=media-usb.mount
Wants=media-usb.mount

[Service]
Type=simple
User=silver
WorkingDirectory=/home/silver/sante
Environment=PATH=/home/silver/venv/bin:/usr/bin
ExecStart=/home/silver/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> **Notas sobre la configuración real:**
> - El venv está en `/home/silver/venv`, **fuera** del directorio del proyecto.
> - El servicio depende de `media-usb.mount`: si el USB de backups no está
>   montado, el servicio no arranca. Verificar el USB antes de reiniciar.

### 2. Activar y arrancar

```bash
sudo systemctl daemon-reload
sudo systemctl enable sante
sudo systemctl start sante
```

### 3. Verificar estado

```bash
sudo systemctl status sante
```

### 4. Ver logs en tiempo real

```bash
sudo journalctl -u sante -f
```

---

## Montar USB para backups

### 1. Identificar el USB

```bash
lsblk
```

Buscar el dispositivo (ej: `/dev/sda1`).

### 2. Crear punto de montaje

```bash
sudo mkdir -p /mnt/usb-backup
```

### 3. Montar automáticamente al arrancar

```bash
sudo blkid /dev/sda1
```

Anotar el UUID. Editar fstab:

```bash
sudo nano /etc/fstab
```

Añadir al final:

```
UUID=<uuid-del-usb> /mnt/usb-backup ext4 defaults,nofail 0 2
```

> Si el USB es NTFS: `UUID=<uuid> /mnt/usb-backup ntfs-3g defaults,nofail 0 0`

### 4. Montar y verificar

```bash
sudo mount -a
ls /mnt/usb-backup
```

### 5. Enlazar carpeta de backups al USB

```bash
rm -rf /home/sante/sante/backups
ln -s /mnt/usb-backup /home/sante/sante/backups
```

---

## Backup automático diario (cron)

```bash
crontab -e
```

Añadir:

```
0 3 * * * cp /home/sante/sante/sante.db /mnt/usb-backup/sante_$(date +\%Y\%m\%d).db
0 4 * * * find /mnt/usb-backup -name "sante_*.db" -mtime +30 -delete
```

Esto:
- Copia la BD al USB cada día a las 3:00
- Elimina backups de más de 30 días a las 4:00

---

## IP fija en la red local

Para que la Raspberry siempre tenga la misma IP:

```bash
sudo nmcli con mod "Wired connection 1" ipv4.addresses 192.168.1.100/24
sudo nmcli con mod "Wired connection 1" ipv4.gateway 192.168.1.1
sudo nmcli con mod "Wired connection 1" ipv4.dns "8.8.8.8 8.8.4.4"
sudo nmcli con mod "Wired connection 1" ipv4.method manual
sudo nmcli con up "Wired connection 1"
```

> Ajustar la IP (`192.168.1.100`), gateway y nombre de conexión según tu red. Verificar con `ip addr`.

---

## Acceso desde dispositivos de la clínica

Una vez configurada la IP fija, todos los dispositivos acceden a:

```
http://192.168.1.100:8000
```

Para un acceso más cómodo, configurar en el router un nombre DNS local o usar `sante-server.local` (mDNS, funciona por defecto en Raspberry Pi OS).

---

## Seguridad básica

### Cambiar contraseña SSH

```bash
passwd
```

### Desactivar login con contraseña (usar solo clave SSH)

```bash
ssh-keygen -t ed25519  # en tu PC
ssh-copy-id sante@sante-server.local

# En la Raspberry:
sudo nano /etc/ssh/sshd_config
# Cambiar: PasswordAuthentication no
sudo systemctl restart ssh
```

### Firewall

```bash
sudo apt install -y ufw
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # App
sudo ufw enable
```

---

## Actualizar la aplicación

```bash
cd /home/sante/sante
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sante
```

> Si hay cambios en modelos de BD, hacer backup antes y re-ejecutar `python seed.py` (solo añade datos nuevos, no borra existentes).

---

## Solución de problemas

### La app no arranca

```bash
sudo systemctl status sante
sudo journalctl -u sante --since "5 min ago"
```

### No se puede acceder desde la red

```bash
# Verificar que el servicio escucha
ss -tlnp | grep 8000

# Verificar firewall
sudo ufw status
```

### Error de permisos en USB

```bash
sudo chown -R sante:sante /mnt/usb-backup
```

### La Raspberry se queda sin espacio

```bash
df -h
# Limpiar logs antiguos
sudo journalctl --vacuum-time=7d
```

### Reiniciar la app

```bash
sudo systemctl restart sante
```

### Reiniciar la Raspberry

```bash
sudo reboot
```

---

## Resumen de puertos y rutas (valores REALES de producción)

| Elemento | Valor |
|----------|-------|
| Puerto app | `8000` |
| Usuario sistema | `silver` |
| Home | `/home/silver` |
| Proyecto | `/home/silver/sante` |
| Entorno virtual | `/home/silver/venv` (fuera del proyecto) |
| Base de datos | `/home/silver/sante/sante.db` |
| Backups (montaje USB) | `media-usb.mount` (verificar punto de montaje real con `mount \| grep usb`) |
| Uploads (PDFs) | `/home/silver/sante/uploads/` |
| Logs errores | `/home/silver/sante/app/logs/errors.log` |
| Servicio systemd | `sante.service` (`User=silver`, requiere `media-usb.mount`) |
| IP actual (casa) | `192.168.0.100` |
