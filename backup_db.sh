#!/usr/bin/env bash
#
# backup_db.sh — Copia de seguridad diaria de la base de datos de Santé.
#
# Pensado para ejecutarse desde cron (una vez al día). Es robusto ante apagones:
# si un día la Raspberry está apagada, ese día simplemente no hay copia; al día
# siguiente que esté encendida, cron lo ejecuta con normalidad. No se rompe nada.
#
# Qué hace:
#   1. Comprueba que el USB de backups está montado (si no, NO escribe en la SD).
#   2. Copia diaria: sante_diaria.db (sobrescribe la del día anterior).
#   3. El día 1 de cada mes: copia mensual persistente sante_mensual_YYYYMM.db.
#   4. Rota (borra) las copias mensuales de más de RETENTION_MONTHS meses.
#   5. Solo copia el .db (los documentos ya viven en el USB de forma permanente).
#
# Uso (cron): 0 3 * * * /home/silver/sante/backup_db.sh >> /home/silver/sante/app/logs/backup.log 2>&1

set -uo pipefail

# --- Configuración ---
PROJECT_DIR="/home/silver/sante"
DB_FILE="${PROJECT_DIR}/sante.db"
BACKUP_DIR="/media/usb/backups"       # debe estar en el USB (punto de montaje)
MOUNT_POINT="/media/usb"              # se comprueba que esté montado
RETENTION_MONTHS=12                   # meses de copias mensuales a conservar

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*"; }

# --- 1. Comprobaciones ---
if [ ! -f "${DB_FILE}" ]; then
  log "ERROR: no se encuentra la BD en ${DB_FILE}. Abortado."
  exit 1
fi

# El USB debe estar montado; si no, NO escribimos (evita llenar la SD por error).
if ! mountpoint -q "${MOUNT_POINT}"; then
  log "ERROR: el USB no está montado en ${MOUNT_POINT}. Backup omitido (se reintentará mañana)."
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

# --- 2. Copia diaria (sobrescribe) ---
DAILY="${BACKUP_DIR}/sante_diaria.db"
if command -v sqlite3 >/dev/null 2>&1; then
  # .backup hace una copia consistente aunque la BD esté en uso.
  sqlite3 "${DB_FILE}" ".backup '${DAILY}'"
else
  cp "${DB_FILE}" "${DAILY}"
fi
log "Backup diario actualizado: ${DAILY}"

# --- 3. Copia mensual persistente el día 1 ---
if [ "$(date +%d)" = "01" ]; then
  MONTHLY="${BACKUP_DIR}/sante_mensual_$(date +%Y%m).db"
  if [ ! -f "${MONTHLY}" ]; then
    cp "${DAILY}" "${MONTHLY}"
    log "Backup mensual creado: ${MONTHLY}"
  fi
fi

# --- 4. Rotación: borrar copias mensuales de más de RETENTION_MONTHS meses ---
# Se basa en la fecha de modificación del fichero. Solo afecta a sante_mensual_*.db.
find "${BACKUP_DIR}" -name 'sante_mensual_*.db' -type f -mtime +$((RETENTION_MONTHS * 31)) -print -delete \
  | while read -r f; do log "Rotación: eliminado backup mensual antiguo ${f}"; done

log "Backup completado correctamente."
exit 0
