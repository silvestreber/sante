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
#   8. Muestra un resumen final: OK o FALLO (con el detalle del error).
#
# Uso:
#   ./deploy.sh
#
# Requisitos: ejecutarse como el usuario 'silver' desde /home/silver/sante,
# con el virtualenv en /home/silver/venv y el servicio 'sante.service'.

set -uo pipefail

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

# --- Control de estado para el resumen final ---
CURRENT_STEP="inicio"
BACKUP_PATH=""
DEPLOY_PULLED="no"
DEPS_INSTALLED="no"
MIGRATIONS_OUTPUT=""

# Marca el paso actual (para saber qué falló si algo peta)
step() { CURRENT_STEP="$1"; info "$1"; }

# Manejador de fallo: se dispara ante cualquier error no controlado.
on_error() {
  local exit_code=$?
  echo
  err "=================================================="
  err " DESPLIEGUE FALLIDO"
  err "=================================================="
  err " Paso que falló : ${CURRENT_STEP}"
  err " Código de error: ${exit_code}"
  if [ -n "${BACKUP_PATH}" ]; then
    err " Backup previo  : ${BACKUP_PATH}"
    err " (puedes restaurar la BD desde ese fichero si hiciera falta)"
  fi
  err " Revisa los logs del servicio con:"
  err "   sudo journalctl -u ${SERVICE_NAME} --since '5 min ago'"
  err "=================================================="
  exit "${exit_code}"
}
trap on_error ERR

# --- 1. Comprobaciones previas ---
step "1/7 Comprobaciones previas"
cd "${PROJECT_DIR}" || { err "No existe ${PROJECT_DIR}"; exit 1; }
[ -d ".git" ] || { err "No es un repositorio git: ${PROJECT_DIR}"; exit 1; }
[ -x "${PYTHON}" ] || { err "No se encuentra el intérprete del venv: ${PYTHON}"; exit 1; }

# --- 2. Backup de la base de datos ANTES de nada ---
step "2/7 Backup de la base de datos"
if [ -f "${DB_FILE}" ]; then
  mkdir -p "${BACKUP_DIR}"
  TS="$(date +%Y%m%d_%H%M%S)"
  BACKUP_PATH="${BACKUP_DIR}/sante_predeploy_${TS}.db"
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "${DB_FILE}" ".backup '${BACKUP_PATH}'"
  else
    cp "${DB_FILE}" "${BACKUP_PATH}"
  fi
  ok "Backup creado: ${BACKUP_PATH}"
else
  warn "No se encontró ${DB_FILE}; se omite el backup (¿primer despliegue?)."
fi

# --- 3. Descargar código nuevo ---
step "3/7 Descargar código del repositorio"
REQ_HASH_BEFORE="$(sha1sum requirements.txt 2>/dev/null | awk '{print $1}' || true)"
git fetch --prune origin
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
REV_BEFORE="$(git rev-parse HEAD)"
git pull --ff-only origin "${CURRENT_BRANCH}"
REV_AFTER="$(git rev-parse HEAD)"
if [ "${REV_BEFORE}" != "${REV_AFTER}" ]; then
  DEPLOY_PULLED="sí (${REV_BEFORE:0:7} -> ${REV_AFTER:0:7})"
  ok "Código actualizado: ${DEPLOY_PULLED}"
else
  DEPLOY_PULLED="no (ya estaba al día)"
  ok "El código ya estaba al día."
fi

# --- 4. Dependencias (solo si cambió requirements.txt) ---
step "4/7 Dependencias"
REQ_HASH_AFTER="$(sha1sum requirements.txt 2>/dev/null | awk '{print $1}' || true)"
if [ "${REQ_HASH_BEFORE}" != "${REQ_HASH_AFTER}" ]; then
  info "requirements.txt cambió; instalando dependencias..."
  "${PIP}" install -r requirements.txt
  DEPS_INSTALLED="sí"
  ok "Dependencias instaladas."
else
  info "requirements.txt sin cambios; se omiten dependencias."
fi

# --- 5. Migraciones de BD ---
step "5/7 Migraciones de base de datos"
MIGRATIONS_OUTPUT="$("${PYTHON}" -m migrations.runner)"
echo "${MIGRATIONS_OUTPUT}"
ok "Migraciones al día."

# --- 6. Reiniciar el servicio ---
step "6/7 Reiniciar el servicio ${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

# --- 7. Healthcheck ---
step "7/7 Healthcheck"
sleep 3
HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' "${HEALTH_URL}" || echo '000')"
if [ "${HTTP_CODE}" != "200" ] && [ "${HTTP_CODE}" != "302" ]; then
  err "La app no respondió correctamente (HTTP ${HTTP_CODE})."
  # Forzamos el manejador de error con contexto de healthcheck
  CURRENT_STEP="7/7 Healthcheck (HTTP ${HTTP_CODE})"
  false
fi

# --- Resumen final OK ---
echo
ok "=================================================="
ok " DESPLIEGUE COMPLETADO CORRECTAMENTE"
ok "=================================================="
ok " Rama            : ${CURRENT_BRANCH}"
ok " Código          : ${DEPLOY_PULLED}"
ok " Dependencias    : ${DEPS_INSTALLED}"
ok " Migraciones     : $(echo "${MIGRATIONS_OUTPUT}" | tail -n 1)"
[ -n "${BACKUP_PATH}" ] && ok " Backup previo   : ${BACKUP_PATH}"
ok " App responde    : HTTP ${HTTP_CODE}"
ok "=================================================="
exit 0
