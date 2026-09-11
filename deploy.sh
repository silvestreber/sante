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
# ROLLBACK AUTOMÁTICO:
#   Si el despliegue falla DESPUÉS de reiniciar el servicio (p.ej. la versión
#   nueva no arranca y el healthcheck no responde), el script revierte solo:
#   vuelve el código al commit anterior (git reset --hard), restaura la BD desde
#   el backup previo (lo que además deshace cualquier migración aplicada) y
#   reinicia el servicio con la versión antigua, verificando que responde.
#   Si el fallo ocurre ANTES del reinicio (pull, deps o migraciones), el servicio
#   antiguo sigue intacto y solo se revierte el código descargado; no hay rollback
#   de BD porque nada se tocó en caliente.
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
MAX_ATTEMPTS=20   # healthcheck: 20 intentos x 2s = hasta 40s de margen

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

# --- Puntos de restauración para el rollback automático ---
REV_BEFORE=""        # commit git antes del pull (para revertir el código)
RESTART_DONE="no"    # ¿ya se reinició el servicio con la versión nueva?
ROLLBACK_DONE="no"   # evita rollback recursivo

# Marca el paso actual (para saber qué falló si algo peta)
step() { CURRENT_STEP="$1"; info "$1"; }

# --- Rollback automático: revierte código + BD y reinicia el servicio ---
# Solo tiene sentido cuando ya se tocó "en caliente" (reinicio con código nuevo).
do_rollback() {
  [ "${ROLLBACK_DONE}" = "sí" ] && return 0
  ROLLBACK_DONE="sí"
  echo
  warn "--------------------------------------------------"
  warn " INICIANDO ROLLBACK AUTOMÁTICO"
  warn "--------------------------------------------------"

  # 1. Revertir el código al commit anterior (si hubo pull).
  if [ -n "${REV_BEFORE}" ]; then
    warn " Revirtiendo código a ${REV_BEFORE:0:7} ..."
    if git reset --hard "${REV_BEFORE}" >/dev/null 2>&1; then
      ok " Código revertido a ${REV_BEFORE:0:7}."
    else
      err " No se pudo revertir el código con git reset --hard ${REV_BEFORE:0:7}."
    fi
  else
    warn " No hay commit previo registrado; se omite la reversión de código."
  fi

  # 2. Restaurar la BD desde el backup previo (si existe).
  if [ -n "${BACKUP_PATH}" ] && [ -f "${BACKUP_PATH}" ]; then
    warn " Restaurando la base de datos desde el backup previo ..."
    if cp "${BACKUP_PATH}" "${DB_FILE}"; then
      ok " Base de datos restaurada desde ${BACKUP_PATH}."
    else
      err " No se pudo restaurar la BD desde ${BACKUP_PATH}."
    fi
  else
    warn " No hay backup de BD para restaurar (¿primer despliegue?)."
  fi

  # 3. Reiniciar el servicio con la versión antigua ya restaurada.
  warn " Reiniciando el servicio ${SERVICE_NAME} con la versión anterior ..."
  sudo systemctl restart "${SERVICE_NAME}" || err " Fallo al reiniciar el servicio en el rollback."

  # 4. Verificar que la versión antigua responde tras el rollback.
  local code="000"
  for attempt in $(seq 1 "${MAX_ATTEMPTS:-20}"); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "${HEALTH_URL}")" || code="000"
    if [ "${code}" = "200" ] || [ "${code}" = "302" ]; then
      ok " La versión anterior responde de nuevo (HTTP ${code})."
      break
    fi
    sleep 2
  done
  if [ "${code}" != "200" ] && [ "${code}" != "302" ]; then
    err " ATENCIÓN: la versión anterior NO responde tras el rollback (HTTP ${code})."
    err " Requiere intervención manual. Revisa:"
    err "   sudo journalctl -u ${SERVICE_NAME} --since '5 min ago'"
  fi
  warn "--------------------------------------------------"
}

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
  fi

  # Si el fallo ocurrió DESPUÉS de reiniciar el servicio (versión nueva ya activa),
  # hacemos rollback automático. Si fue antes, el servicio antiguo sigue intacto.
  if [ "${RESTART_DONE}" = "sí" ]; then
    err " El servicio ya se había reiniciado con la versión nueva -> ROLLBACK."
    do_rollback
  else
    warn " El fallo ocurrió antes de reiniciar el servicio."
    warn " La versión ANTERIOR sigue en ejecución sin cambios; no hace falta rollback."
    if [ -n "${REV_BEFORE}" ]; then
      REV_NOW="$(git rev-parse HEAD 2>/dev/null || echo '')"
      if [ -n "${REV_NOW}" ] && [ "${REV_NOW}" != "${REV_BEFORE}" ]; then
        warn " Revirtiendo el código descargado para dejar el repo como estaba ..."
        git reset --hard "${REV_BEFORE}" >/dev/null 2>&1 \
          && ok " Código devuelto a ${REV_BEFORE:0:7}." \
          || err " No se pudo revertir el código; hazlo manual: git reset --hard ${REV_BEFORE:0:7}"
      fi
    fi
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
REV_BEFORE="$(git rev-parse HEAD)"   # punto de restauración para el rollback
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
RESTART_DONE="sí"   # a partir de aquí, un fallo dispara ROLLBACK automático

# --- 7. Healthcheck (con reintentos: la Raspberry puede tardar en arrancar) ---
step "7/7 Healthcheck"
HTTP_CODE="000"
for attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
  HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' "${HEALTH_URL}")" || HTTP_CODE="000"
  if [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "302" ]; then
    ok "App lista tras ${attempt} intento(s) (HTTP ${HTTP_CODE})."
    break
  fi
  info "Esperando a que la app arranque... (intento ${attempt}/${MAX_ATTEMPTS}, HTTP ${HTTP_CODE})"
  sleep 2
done
if [ "${HTTP_CODE}" != "200" ] && [ "${HTTP_CODE}" != "302" ]; then
  err "La app (versión nueva) no respondió tras ${MAX_ATTEMPTS} intentos (HTTP ${HTTP_CODE})."
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
