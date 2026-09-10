#!/usr/bin/env bash
#
# deploy.sh — Actualiza Santé en producción (Raspberry Pi) de forma segura.
#
# Pasos:
#   1. Comprueba que estamos en la raíz del proyecto y en un repo git.
#   2. Hace backup de la base de datos ANTES de tocar nada.
#   3. Descarga el código nuevo (git pull, fast-forward).
#   4. Instala dependencias si cambió requirements.txt.
#   5. Aplica migraciones de BD pendientes (si no hay, no hace nada).
#   6. Reinicia el servicio systemd.
#   7. Verifica que la app responde (healthcheck).
#
# Uso:
#   ./deploy.sh
#
# Requisitos: ejecutarse como el usuario 'silver' desde /home/silver/sante,
# con el virtualenv en /home/silver/venv y el servicio 'sante.service'.

set -euo pipefail

# --- Configuración (ajustable) ---
PROJECT_DIR="/home/silver/sante"
VENV_DIR="/home/silver/venv"
SERVICE_NAME="sante"
DB_FILE="sante.db"
BACKUP_DIR="${PROJECT_DIR}/backups"
HEALTH_URL="http://127.0.0.1:8000/login"
PYTHON="${VENV_DIR}/bin/python"
PIP="${VENV_DIR}/bin/pip"

# --- Colores para legibilidad ---
info()  { echo -e "\033[1;34m[deploy]\033[0m $*"; }
ok()    { echo -e "\033[1;32m[deploy]\033[0m $*"; }
warn()  { echo -e "\033[1;33m[deploy]\033[0m $*"; }
err()   { echo -e "\033[1;31m[deploy]\033[0m $*" >&2; }

# --- 1. Comprobaciones previas ---
cd "${PROJECT_DIR}" || { err "No existe ${PROJECT_DIR}"; exit 1; }

if [ ! -d ".git" ]; then
  err "No es un repositorio git: ${PROJECT_DIR}"
  exit 1
fi

if [ ! -x "${PYTHON}" ]; then
  err "No se encuentra el intérprete del venv: ${PYTHON}"
  exit 1
fi

# --- 2. Backup de la base de datos ANTES de nada ---
if [ -f "${DB_FILE}" ]; then
  mkdir -p "${BACKUP_DIR}"
  TS="$(date +%Y%m%d_%H%M%S)"
  BACKUP_PATH="${BACKUP_DIR}/sante_predeploy_${TS}.db"
  # Copia consistente si hay sqlite3; si no, copia simple.
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "${DB_FILE}" ".backup '${BACKUP_PATH}'"
  else
    cp "${DB_FILE}" "${BACKUP_PATH}"
  fi
  ok "Backup de la BD creado: ${BACKUP_PATH}"
else
  warn "No se encontró ${DB_FILE}; se omite el backup (¿primer despliegue?)."
fi

# --- 3. Descargar código nuevo ---
info "Descargando cambios del repositorio..."
REQ_HASH_BEFORE="$(sha1sum requirements.txt 2>/dev/null | awk '{print $1}' || true)"
git fetch --prune origin
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
git pull --ff-only origin "${CURRENT_BRANCH}"
ok "Código actualizado (rama ${CURRENT_BRANCH})."

# --- 4. Dependencias (solo si cambió requirements.txt) ---
REQ_HASH_AFTER="$(sha1sum requirements.txt 2>/dev/null | awk '{print $1}' || true)"
if [ "${REQ_HASH_BEFORE}" != "${REQ_HASH_AFTER}" ]; then
  info "requirements.txt cambió; instalando dependencias..."
  "${PIP}" install -r requirements.txt
  ok "Dependencias instaladas."
else
  info "requirements.txt sin cambios; se omiten dependencias."
fi

# --- 5. Migraciones de BD ---
info "Comprobando migraciones pendientes..."
"${PYTHON}" -m migrations.runner
ok "Migraciones al día."

# --- 6. Reiniciar el servicio ---
info "Reiniciando el servicio ${SERVICE_NAME}..."
sudo systemctl restart "${SERVICE_NAME}"

# --- 7. Healthcheck ---
info "Verificando que la app responde..."
sleep 3
HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' "${HEALTH_URL}" || echo '000')"
if [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "302" ]; then
  ok "App respondiendo (HTTP ${HTTP_CODE}). Despliegue completado."
else
  err "La app no respondió correctamente (HTTP ${HTTP_CODE})."
  err "Revisa los logs: sudo journalctl -u ${SERVICE_NAME} --since '2 min ago'"
  exit 1
fi
