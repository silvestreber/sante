# Configuración de producción — Santé (Raspberry Pi)

Guía paso a paso para configurar el entorno de producción.

---

## 1. Configurar email de IONOS

Los correos (recordatorios, facturas, consentimientos) se enviarán desde la cuenta de IONOS de la clínica.

### Datos necesarios

Pedir al cliente:
- Email de IONOS (ej: `info@clinicasante.es`)
- Contraseña del buzón

### Pasos

1. Conectar a la Raspberry por SSH:
   ```bash
   ssh pi@<ip-raspberry>
   ```

2. Editar el archivo `.env` del proyecto:
   ```bash
   nano /ruta/al/proyecto/sante/.env
   ```

3. Cambiar las líneas SMTP:
   ```
   SMTP_HOST=smtp.ionos.es
   SMTP_PORT=587
   SMTP_USER=info@clinicasante.es
   SMTP_PASSWORD=la-contraseña-del-buzon
   SMTP_FROM=info@clinicasante.es
   ```

4. Reiniciar la aplicación:
   ```bash
   sudo systemctl restart sante
   ```

5. **Verificar**: desde la app, enviar un documento por email a una dirección conocida y comprobar que llega.

### Notas

- IONOS usa STARTTLS en puerto 587 (igual que Gmail), no hay que tocar código.
- Si no funciona con puerto 587, probar con puerto 465 (SSL). En ese caso hay que modificar `app/email_service.py`:
  ```python
  # Cambiar esta línea:
  with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
      server.starttls()
  # Por esta:
  with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
  ```
- No se necesita "contraseña de aplicación" como en Gmail. Se usa la contraseña normal del buzón.

---

## 2. Configurar USB para documentos (uploads)

Los documentos adjuntos de pacientes (radiografías, informes, fotos) se almacenan en una USB montada en la Raspberry.

### Preparar la USB

1. Conectar la USB a la Raspberry.

2. Identificar el dispositivo:
   ```bash
   lsblk
   ```
   Buscar algo como `/dev/sda1`.

3. (Solo la primera vez) Formatear en ext4:
   ```bash
   sudo mkfs.ext4 /dev/sda1
   ```
   ⚠️ Esto borra todo el contenido de la USB.

4. Crear punto de montaje:
   ```bash
   sudo mkdir -p /mnt/usb
   ```

5. Montar:
   ```bash
   sudo mount /dev/sda1 /mnt/usb
   ```

6. Obtener el UUID para montaje permanente:
   ```bash
   sudo blkid /dev/sda1
   ```
   Copiar el valor UUID (ej: `a1b2c3d4-...`).

7. Configurar montaje automático al arrancar:
   ```bash
   sudo nano /etc/fstab
   ```
   Añadir al final:
   ```
   UUID=a1b2c3d4-xxxx-xxxx-xxxx /mnt/usb ext4 defaults,nofail 0 2
   ```
   > `nofail` evita que la Raspberry no arranque si la USB no está conectada.

8. Crear la estructura de carpetas:
   ```bash
   sudo mkdir -p /mnt/usb/sante/uploads
   sudo mkdir -p /mnt/usb/sante/backups
   sudo chown -R pi:pi /mnt/usb/sante
   ```

### Configurar la app para usar la USB

1. Editar `.env`:
   ```bash
   nano /ruta/al/proyecto/sante/.env
   ```

2. Cambiar la ruta de uploads:
   ```
   UPLOADS_PATH=/mnt/usb/sante/uploads
   BACKUPS_PATH=/mnt/usb/sante/backups
   ```

3. Reiniciar la app:
   ```bash
   sudo systemctl restart sante
   ```

4. **Verificar**: subir un documento a un paciente desde la app y comprobar que aparece en `/mnt/usb/sante/uploads/`.

### Notas

- Los documentos se organizan en subcarpetas por ID de paciente: `/mnt/usb/sante/uploads/51/archivo.pdf`
- Los PDFs de facturas se guardan en `app/static/invoices/` (dentro del proyecto, no en la USB), ya que se regeneran automáticamente.
- Si la USB se desconecta, la app sigue funcionando pero no se podrán subir ni ver documentos adjuntos.

---

## 3. Configurar documento de protección de datos

El documento de protección de datos es un PDF estático que se envía por email a los pacientes para que lo firmen. Se encuentra en:

```
app/static/docs/proteccion_de_datos.pdf
```

### Cambiar el documento

1. Obtener del cliente el PDF definitivo del documento de protección de datos.

2. Copiar el archivo a la Raspberry:
   ```bash
   scp proteccion_de_datos.pdf pi@<ip-raspberry>:/ruta/al/proyecto/sante/app/static/docs/proteccion_de_datos.pdf
   ```

   O directamente en la Raspberry:
   ```bash
   cp /ruta/al/nuevo/documento.pdf /ruta/al/proyecto/sante/app/static/docs/proteccion_de_datos.pdf
   ```

3. **No hace falta reiniciar** la app. El archivo se lee en cada envío.

4. **Verificar**: desde la ficha de un paciente, pulsar el botón "Enviar" junto al consentimiento y comprobar que llega el PDF correcto.

### Notas

- El nombre del archivo **debe ser exactamente** `proteccion_de_datos.pdf`.
- Si se quiere cambiar el nombre o la ruta, hay que modificar la constante `DATA_PROTECTION_PDF` en `app/routers/documents.py`.
- El botón "Enviar" aparece en la ficha del paciente junto al estado del consentimiento (tanto si está firmado como si no).
- Solo se puede enviar si el paciente tiene email registrado. Si no lo tiene, la app muestra un error.

---

## Resumen de archivos a configurar

| Qué | Dónde | Variable .env |
|-----|-------|---------------|
| Email IONOS | `.env` | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` |
| Documentos pacientes | USB montada | `UPLOADS_PATH=/mnt/usb/sante/uploads` |
| Backups | USB montada | `BACKUPS_PATH=/mnt/usb/sante/backups` |
| Consentimientos firmados | Carpeta local o USB | `SIGNED_DOCS_PATH=/mnt/usb/sante/consentimientos` |
| Plantillas consentimiento | `app/static/docs/*.docx` | (ruta fija en código) |

---

## 4. Configurar directorio de consentimientos firmados

Los consentimientos firmados (PDFs generados con datos del paciente) se guardan en una carpeta configurable.

### Pasos

1. Crear la carpeta (en la USB o donde se prefiera):
   ```bash
   sudo mkdir -p /mnt/usb/sante/consentimientos
   sudo chown pi:pi /mnt/usb/sante/consentimientos
   ```

2. Editar `.env` y añadir:
   ```
   SIGNED_DOCS_PATH=/mnt/usb/sante/consentimientos
   ```

3. Reiniciar la app:
   ```bash
   sudo systemctl restart sante
   ```

4. **Verificar**: firmar un consentimiento desde la ficha de un paciente y comprobar que el PDF aparece en la carpeta.

### Plantillas de consentimiento

Las plantillas `.docx` están en `app/static/docs/`. Para añadir nuevas plantillas:
1. Crear el documento en Word con los marcadores: `{{nombre_paciente}}`, `{{dni_paciente}}`, `{{día_firma}}`, `{{mes_firma}}`, `{{mes_firma_num}}`, `{{ano_firma}}`, `{{fisio_firma}}`, `{{dni_fisio_firma}}`, `{{ud_fisioterapia}}`, `{{nombre_tutor}}`, `{{relacion_tutor}}`, `{{dni_tutor}}`, `{{observaciones}}`
2. Guardar como `.docx` en `app/static/docs/`
3. Aparecerá automáticamente en el selector de la app (no hace falta reiniciar)

### Nota sobre docx2pdf en Raspberry Pi

`docx2pdf` usa Microsoft Word en Windows y LibreOffice en Linux. En la Raspberry:
```bash
sudo apt install libreoffice
```

---

## Verificación final

Tras configurar todo:

1. ✅ Enviar un email de prueba (factura o consentimiento) → debe llegar desde la cuenta de IONOS
2. ✅ Subir un documento a un paciente → debe guardarse en `/mnt/usb/sante/uploads/`
3. ✅ Firmar un consentimiento desde la ficha del paciente → debe generarse el PDF en la carpeta de consentimientos
4. ✅ Enviar consentimiento firmado por email → debe llegar el PDF correcto
5. ✅ Hacer un backup desde Configuración > Backup → debe descargarse el archivo .db
