# Despliegue de Santé en Producción (Raspberry Pi)

Guía única de despliegue. Reúne y sustituye a los antiguos `DESPLIEGUE_PRODUCCION.md`
y `DESPLIEGUE_RASPBERRY.md`.

- **Parte A — Actualizar en el día a día** (lo habitual): `git pull` + `./deploy.sh`.
- **Parte B — Instalación desde cero** (solo la primera vez o si se reinstala la Pi).
- **Parte C — Solución de problemas y referencia.**

---

## Datos reales de producción (verificados)

| Elemento | Valor real |
|----------|------------|
| Usuario del sistema | `silver` |
| Home | `/home/silver` |
| Proyecto | `/home/silver/sante` |
| Entorno virtual (venv) | `/home/silver/venv` (**fuera** del proyecto) |
| Python del venv | `/home/silver/venv/bin/python` |
| Base de datos | `/home/silver/sante/sante.db` |
| Servicio systemd | `sante.service` (`User=silver`) |
| Dependencia de montaje | `media-usb.mount` (el servicio la requiere para arrancar) |
| USB de backups | `/dev/sda1` montado en `/media/usb` (ext4) |
| Backups del deploy | `/home/silver/sante/backups/` |
| SO | Raspberry Pi OS Lite (Debian 13 *trixie*), **solo consola** |
| IP en red local | `192.168.0.100` |
| Puerto app | `8000` |
| Acceso | SSH (`ssh silver@192.168.0.100`) o teclado + monitor |
| Repositorio | `https://github.com/silvestreber/sante.git` (rama `main`) |

> La contraseña del usuario `silver` se definió al flashear con Raspberry Pi Imager.
> Guárdala en un gestor de contraseñas. Si se pierde, se recupera montando la microSD
> en un PC y reseteando la contraseña (sin perder datos).

---

# Parte A — Actualizar la app (uso habitual)

Este es el procedimiento normal para llevar cambios de GitHub a producción. El script
`deploy.sh` se encarga de todo de forma segura: **hace backup del `.db` antes de tocar nada**,
actualiza el código, instala dependencias si cambiaron, aplica migraciones, reinicia el
servicio y verifica que la app responde.

## 1. Conectar a la Raspberry

```bash
ssh silver@192.168.0.100
```

## 2. Comprobaciones previas (recomendado)

```bash
cd /home/silver/sante

# El árbol debe estar limpio; si hay cambios locales no deseados, revísalos antes.
git status

# El USB debe estar montado (el servicio depende de él y ahí van los backups).
systemctl status media-usb.mount --no-pager
df -h | grep -E 'usb|media'
```

> Si `git status` muestra `deploy.sh` modificado solo por el bit de permiso
> (`old mode 100644` → `new mode 100755` en `git diff`), es inofensivo: se descarta
> con `git checkout -- deploy.sh` y luego se vuelve a dar permiso con `chmod +x deploy.sh`
> tras el pull.

## 3. Traer el código y desplegar

```bash
cd /home/silver/sante
git pull --ff-only origin main
chmod +x deploy.sh   # asegura permiso de ejecución tras el pull
./deploy.sh
```

## 4. Qué hace y qué esperar

`deploy.sh` ejecuta 7 pasos y muestra un resumen final en verde (**DESPLIEGUE COMPLETADO
CORRECTAMENTE**) o en rojo (**DESPLIEGUE FALLIDO**, indicando el paso que falló y el backup previo):

1. Comprobaciones previas (proyecto, repo git, venv).
2. **Backup de la BD** → `backups/sante_predeploy_<fecha>.db` (con `sqlite3 .backup`).
3. `git pull` (fast-forward).
4. Dependencias: solo reinstala si cambió `requirements.txt`.
5. Migraciones de BD pendientes (sistema propio en `migrations/`; si no hay, no hace nada).
6. Reinicia `sante.service` (`sudo systemctl restart sante`; puede pedir contraseña de sudo).
7. **Healthcheck con reintentos**: consulta `http://127.0.0.1:8000/login` cada 2 s hasta 20 veces
   (hasta 40 s de margen). La app tarda ~11 s en arrancar en la Pi, así que es normal ver varios
   mensajes de "Esperando a que la app arranque..." antes del `HTTP 200`.

Si el healthcheck no responde tras los 20 intentos, el despliegue se marca como fallido y se
indica el backup previo para poder restaurar si hiciera falta.

## 5. Verificación manual (opcional)

```bash
sudo systemctl status sante --no-pager
```

Y desde un navegador de la red local: `http://192.168.0.100:8000`

---

# Parte B — Instalación desde cero

Solo necesario la primera vez o si se reinstala la Raspberry. En el día a día usa la **Parte A**.

## B.1 Preparar el sistema operativo

Flashear **Raspberry Pi OS Lite (64-bit)** con
[Raspberry Pi Imager](https://www.raspberrypi.com/software/). En la configuración avanzada:

- Activar SSH.
- Configurar usuario `silver` y contraseña (guardarla en gestor de contraseñas).
- Configurar WiFi si no usas Ethernet.
- Establecer hostname.

Al primer arranque, actualizar el sistema e instalar dependencias base:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git sqlite3 libreoffice
```

> `libreoffice` es necesario para generar PDFs de consentimientos en Linux
> (conversión headless con `soffice`/`libreoffice --headless --convert-to pdf`).

## B.2 Preparar el USB de almacenamiento

```bash
# Identificar el USB (normalmente /dev/sda1)
lsblk

# Formatear en ext4 (¡BORRA TODO el contenido del USB!)
sudo umount /dev/sda1 2>/dev/null
sudo mkfs.ext4 -L SANTE_USB /dev/sda1

# Punto de montaje
sudo mkdir -p /media/usb
```

Montaje automático persistente vía `/etc/fstab`:

```bash
sudo blkid /dev/sda1        # anotar el UUID
sudo nano /etc/fstab
```

Añadir al final (usar el UUID real):

```
UUID=<uuid-del-usb> /media/usb ext4 defaults,noatime,nofail 0 2
```

> `nofail` evita que la Raspberry no arranque si el USB no está conectado.

```bash
sudo mount -a
df -h | grep usb          # verificar
```

Estructura de carpetas en el USB y permisos del usuario `silver`:

```bash
sudo mkdir -p /media/usb/{documentos_firmados,facturas,pacientes,backups,logs}
sudo chown -R silver:silver /media/usb
```

## B.3 Obtener el proyecto

```bash
cd /home/silver
git clone https://github.com/silvestreber/sante.git sante
```

## B.4 Crear el entorno virtual (fuera del proyecto)

```bash
cd /home/silver
python3 -m venv venv
source venv/bin/activate
```

## B.5 Instalar dependencias

```bash
cd /home/silver/sante
pip install -r requirements.txt
```

> En Raspberry Pi la compilación de `bcrypt` puede tardar unos minutos. Si falla:
> ```bash
> sudo apt install -y build-essential libffi-dev python3-dev
> ```

## B.6 Configurar variables de entorno (`.env`)

```bash
nano /home/silver/sante/.env
```

Contenido para producción (usar rutas del USB y valores reales; **no** subir el `.env` al repo):

```env
SECRET_KEY=<clave-secreta-larga-y-aleatoria>
SMTP_HOST=smtp.ionos.es
SMTP_PORT=587
SMTP_USER=info@centrosante.es
SMTP_PASSWORD=<contraseña-email-ionos>
SMTP_FROM=info@centrosante.es
CLINIC_NAME=Centro Santé Fisioterapia y Osteopatía
CLINIC_PHONE=636554300
CLINIC_ADDRESS=Calle Valle de la Fuente, 25, Valverde del Camino
CLINIC_CIF=44241271N
AUTO_BACKUP_PATH=/media/usb/backups
SIGNED_DOCS_PATH=/media/usb/documentos_firmados
INVOICES_PATH=/media/usb/facturas
PATIENT_DOCS_PATH=/media/usb/pacientes
LOG_PATH=/media/usb/logs/errors.log
```

> Generar una `SECRET_KEY` segura:
> `python3 -c "import secrets; print(secrets.token_hex(32))"`

Crear también la carpeta de logs local por si el USB no estuviera disponible:

```bash
mkdir -p /home/silver/sante/app/logs
```

## B.7 Inicializar la base de datos

No hace falta un script aparte: la aplicación crea las tablas automáticamente al arrancar
(`init_db()` se ejecuta en el `lifespan` de FastAPI en `app/main.py`). Basta con el arranque
manual del paso siguiente para que se genere `sante.db`.

> Tras el primer arranque, cambiar las contraseñas de los usuarios desde la app
> (Configuración > Usuarios).

## B.8 Verificar arranque manual

```bash
cd /home/silver/sante
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Acceder desde otro dispositivo: `http://192.168.0.100:8000`. Detener con `Ctrl+C`.

## B.9 Configurar el servicio systemd

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

Activar y arrancar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sante
sudo systemctl start sante
sudo systemctl status sante --no-pager
```

## B.10 IP fija en la red local (recomendado)

```bash
sudo nmcli con mod "Wired connection 1" ipv4.addresses 192.168.0.100/24
sudo nmcli con mod "Wired connection 1" ipv4.gateway 192.168.0.1
sudo nmcli con mod "Wired connection 1" ipv4.dns "8.8.8.8 8.8.4.4"
sudo nmcli con mod "Wired connection 1" ipv4.method manual
sudo nmcli con up "Wired connection 1"
```

> Ajustar IP, gateway y nombre de conexión según la red. Verificar con `ip addr`.

## B.11 Backup automático diario (cron, opcional)

Complementa al backup que hace `deploy.sh`. Copia la BD al USB cada noche y limpia los antiguos:

```bash
crontab -e
```

```
0 3 * * * cp /home/silver/sante/sante.db /media/usb/backups/sante_$(date +\%Y\%m\%d).db
0 4 * * * find /media/usb/backups -name "sante_*.db" -mtime +30 -delete
```

## B.12 Seguridad básica

```bash
# Cambiar contraseña del usuario
passwd

# Firewall: permitir solo SSH y la app
sudo apt install -y ufw
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw enable
```

Opcional: acceso SSH solo con clave (`ssh-copy-id` desde tu PC y luego
`PasswordAuthentication no` en `/etc/ssh/sshd_config`).

## B.13 Permisos sudo para acciones desde la app

La app permite, desde **Configuración**, apagar el sistema y reiniciar el servicio
(este último tras cambiar una ruta de almacenamiento). Como el servicio corre como
`silver` sin terminal interactiva, hay que autorizar esos comandos concretos sin
contraseña. Se hace con un fichero en `/etc/sudoers.d/` (permiso mínimo, solo esos comandos):

```bash
echo 'silver ALL=(root) NOPASSWD: /usr/bin/systemctl restart sante.service, /usr/sbin/shutdown' | sudo tee /etc/sudoers.d/sante
sudo chmod 440 /etc/sudoers.d/sante
sudo visudo -c        # validar sintaxis (debe decir "parsed OK")
```

> Verifica primero las rutas reales de los binarios con `which systemctl` y
> `which shutdown` (en Debian 13 suelen ser `/usr/bin/systemctl` y `/usr/sbin/shutdown`).
> Si difieren, ajusta el fichero. Este permiso es acotado: `silver` solo puede reiniciar
> `sante.service` y apagar, nada más. Como la Raspberry no está expuesta a internet
> (solo red local), el riesgo es mínimo.

Prueba que funciona sin pedir contraseña:

```bash
sudo -n systemctl restart sante.service && echo OK
```

> El botón "Reiniciar servicio" de la app (pestaña Almacenamiento) y el botón "Apagar"
> (pestaña Backup) dependen de este permiso. Si no está configurado, esas acciones
> fallarán silenciosamente.

---

# Parte C — Solución de problemas y referencia

## La app no arranca

```bash
sudo systemctl status sante --no-pager
sudo journalctl -u sante --since "5 min ago" --no-pager
```

## No se puede acceder desde la red

```bash
ss -tlnp | grep 8000     # ¿la app escucha?
sudo ufw status          # ¿el firewall bloquea?
```

## El USB no se monta

```bash
sudo mount -a
sudo blkid               # comparar UUID con /etc/fstab
systemctl status media-usb.mount --no-pager
```

> Recuerda: el servicio `sante` depende de `media-usb.mount`. Si el USB no está montado,
> el servicio no arranca.

## Permisos denegados en el USB

```bash
sudo chown -R silver:silver /media/usb
```

## LibreOffice no convierte (consentimientos)

```bash
sudo apt install -y libreoffice
libreoffice --headless --convert-to pdf /tmp/test.docx
```

## La Raspberry se queda sin espacio

```bash
df -h
sudo journalctl --vacuum-time=7d    # limpiar logs antiguos del sistema
```

## Restaurar un backup de la BD

`deploy.sh` deja backups en `/home/silver/sante/backups/sante_predeploy_<fecha>.db`.
Para restaurar:

```bash
sudo systemctl stop sante
cp /home/silver/sante/backups/sante_predeploy_<fecha>.db /home/silver/sante/sante.db
sudo systemctl start sante
```

## Reiniciar / apagar de forma segura

```bash
sudo systemctl restart sante   # reiniciar solo la app
sudo reboot                    # reiniciar la Raspberry
sudo shutdown -h now           # apagar (también desde la app: Configuración > Backup > Apagar)
```

> **Nunca desenchufar sin apagar.** Esperar a que el LED verde deje de parpadear.

## Estructura final en producción

```
/home/silver/sante/          ← Código de la app + BD (sante.db)
/home/silver/sante/backups/  ← Backups pre-despliegue creados por deploy.sh
/home/silver/sante/app/logs/ ← Log de errores (se queda en la SD, es ligero)
/media/usb/                  ← Documentos (pesados) en el USB externo
├── documentos_firmados/     ← PDFs de consentimientos firmados
├── facturas/                ← PDFs de facturas / justificantes
├── pacientes/               ← Documentos adjuntos de pacientes
└── backups/                 ← Backups automáticos diarios/mensuales
```

## Rutas de almacenamiento (configurables desde la app)

Las carpetas de documentos ya no se fijan solo en el `.env`: se configuran desde
**Configuración > Almacenamiento** (solo ADMIN). Ahí se ve el espacio libre de cada
carpeta y se puede cambiar la ubicación (por ejemplo, a un USB nuevo cuando el actual
se llene). Al cambiar una ruta:

- La app comprueba que hay espacio y que no hay ficheros con el mismo nombre en el destino.
  Si los hubiera, avisa y no mueve nada (requiere resolverlo a mano).
- Mueve los ficheros existentes a la nueva carpeta de forma segura (copiar, verificar, borrar).
- El cambio se aplica al **reiniciar el servicio** (botón en la misma pantalla; requiere
  el permiso sudo de la sección B.13).

Los valores iniciales de estas rutas los siembra la migración `0002_storage_paths`
(apuntando a `/media/usb/...`). El log de errores **no** es configurable: siempre en la SD.

## Política del USB externo (qué pasa si falta)

La app **solo escribe documentos en el USB**, nunca en la tarjeta SD. Comportamiento:

- **Si el USB no está montado** (no conectado, o desconectado en caliente): al intentar
  guardar un consentimiento, factura o documento de paciente, la app **devuelve un error
  claro y no guarda nada** (no escribe en la SD por error). El resto de la app sigue
  funcionando (agenda, consultas, etc.), porque la base de datos vive en la SD.
- El estado del USB (montado / no conectado) y su capacidad se ven en
  **Configuración > Almacenamiento**. Si algún USB no está, aparece un aviso en rojo.
- El arranque del sistema y del servicio **no** se bloquea si el USB falta (el montaje usa
  `nofail` y el servicio usa `Wants=`, no `Requires=`). La app arranca; solo se bloquea
  guardar documentos hasta que el USB vuelva.

Comprobar el estado del USB desde consola:

```bash
systemctl status media-usb.mount --no-pager
df -h /media/usb                                  # capacidad y uso
lsblk -o NAME,SIZE,FSTYPE,LABEL,MODEL /dev/sda    # modelo y tamaño del USB
```

## Cambiar el USB (porque está lleno o se quiere sustituir)

Procedimiento seguro para pasar a un USB nuevo sin perder documentos. La idea: montar el
nuevo USB en un punto temporal, dejar que la **app mueva los ficheros** (con sus
comprobaciones de espacio y colisiones), y finalmente dejar el nuevo USB como `/media/usb`.

> **Antes de empezar:** ten a mano el USB nuevo (igual o mayor capacidad que el actual;
> el actual es un SanDisk de ~29 GB, así que 32 GB o más). Hazlo en un momento sin actividad
> en la clínica. Los datos de la BD (`sante.db`) están en la SD y no se tocan.

### Opción recomendada: mover con la app, luego sustituir el punto de montaje

1. **Conecta el USB nuevo** (además del actual). Identifícalo:
   ```bash
   lsblk -o NAME,SIZE,FSTYPE,LABEL,MODEL
   ```
   El actual es `/dev/sda1` (montado en `/media/usb`). El nuevo aparecerá como `/dev/sdb`.

2. **Formatéalo en ext4 y dale una etiqueta** (¡BORRA el contenido del USB nuevo!):
   ```bash
   sudo umount /dev/sdb1 2>/dev/null
   sudo mkfs.ext4 -L SANTE_USB2 /dev/sdb1
   ```

3. **Móntalo en un punto temporal** y da permisos a `silver`:
   ```bash
   sudo mkdir -p /media/usb_nuevo
   sudo mount /dev/sdb1 /media/usb_nuevo
   sudo chown -R silver:silver /media/usb_nuevo
   ```

4. **Desde la app** (Configuración > Almacenamiento), cambia cada categoría de
   `/media/usb/...` a `/media/usb_nuevo/...` (p.ej. `/media/usb_nuevo/facturas`). La app
   moverá los ficheros de forma segura (copiar-verificar-borrar) y avisará si hay
   colisiones o falta espacio. Pulsa **Reiniciar servicio** cuando termine.

5. **Verifica** que los ficheros están en el USB nuevo y que la app los ve. Cuando estés
   seguro, ya puedes retirar el USB antiguo.

6. **(Opcional pero recomendado) Dejar el USB nuevo como `/media/usb` permanente**, para no
   depender del punto temporal. Con la app parada un momento:
   ```bash
   # Obtener el UUID del USB nuevo
   sudo blkid /dev/sdb1
   # Editar fstab: sustituir el UUID viejo por el nuevo en la línea de /media/usb
   sudo nano /etc/fstab
   ```
   Cambia la línea existente para que el UUID nuevo se monte en `/media/usb`, retira la
   línea/punto temporal, y aplica:
   ```bash
   sudo systemctl stop sante
   sudo umount /media/usb /media/usb_nuevo 2>/dev/null
   sudo mount -a
   df -h /media/usb          # debe mostrar el USB nuevo
   ```
   Finalmente, desde la app vuelve a poner las rutas a `/media/usb/...` y reinicia el
   servicio. Así vuelves al punto de montaje estándar con el disco nuevo.

> **Regla de oro:** no borres nada del USB antiguo hasta haber verificado que todos los
> documentos están en el nuevo y la app los abre correctamente. El movimiento de la app ya
> es seguro (no borra el origen hasta verificar la copia), pero una comprobación visual extra
> nunca sobra tratándose de datos de pacientes.
