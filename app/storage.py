"""Gestión centralizada de rutas de almacenamiento de ficheros.

Todas las rutas base (dónde se guardan consentimientos, facturas, documentos de
pacientes y backups) se resuelven aquí, con esta prioridad:

    1. Valor guardado en la tabla `Config` (configurable desde la app).
    2. Variable de entorno (.env).
    3. Valor por defecto según el sistema operativo.

Cada documento guarda en la base de datos únicamente su **ruta relativa** (el
nombre del fichero). La ruta absoluta se reconstruye en tiempo de uso como
`base_de_la_categoria + ruta_relativa`. Así, cambiar la carpeta base no obliga a
reescribir las rutas de cada documento en la BD.

Los ficheros se crean con un **nombre único global** (prefijo corto), de modo que
dos categorías distintas nunca colisionen si en el futuro se fusionan carpetas.

Incluye además utilidades de movimiento seguro de ficheros entre carpetas
(comprobación de espacio, detección de colisiones y copiar-verificar-borrar).
"""
from __future__ import annotations

import os
import shutil
import sys
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.db.models import Config


class StorageUnavailableError(Exception):
    """El almacenamiento (USB) no está disponible: su punto de montaje no está
    activo. Se lanza para impedir escribir en la SD por error."""


# --- Claves de configuración en la tabla Config ---
KEY_SIGNED_DOCS = "storage_signed_docs_path"
KEY_INVOICES = "storage_invoices_path"
KEY_PATIENT_DOCS = "storage_patient_docs_path"
KEY_AUTO_BACKUP = "storage_auto_backup_path"

# Todas las categorías configurables desde la UI (los logs NO: van fijos en la SD).
STORAGE_KEYS = (KEY_SIGNED_DOCS, KEY_INVOICES, KEY_PATIENT_DOCS, KEY_AUTO_BACKUP)

# Variable de entorno asociada a cada clave (fallback si no hay valor en Config).
_ENV_VAR = {
    KEY_SIGNED_DOCS: "SIGNED_DOCS_PATH",
    KEY_INVOICES: "INVOICES_PATH",
    KEY_PATIENT_DOCS: "PATIENT_DOCS_PATH",
    KEY_AUTO_BACKUP: "AUTO_BACKUP_PATH",
}

# Etiqueta legible por categoría (para mensajes y UI).
STORAGE_LABELS = {
    KEY_SIGNED_DOCS: "Consentimientos firmados",
    KEY_INVOICES: "Facturas y justificantes",
    KEY_PATIENT_DOCS: "Documentos de pacientes",
    KEY_AUTO_BACKUP: "Copias de seguridad",
}


def _is_windows() -> bool:
    return sys.platform.startswith("win")


# Directorios bajo los que una ruta se considera "almacenamiento externo" que
# DEBE estar montado (USB). Configurable por entorno si algún día cambia.
_MOUNT_ROOTS = tuple(
    p.strip() for p in os.getenv("STORAGE_MOUNT_ROOTS", "/media,/mnt").split(",") if p.strip()
)
# Permite desactivar la comprobación de montaje (p.ej. si se usa disco interno).
_REQUIRE_MOUNT = os.getenv("STORAGE_REQUIRE_MOUNT", "1") not in ("0", "false", "False", "")


def find_mountpoint(path: str) -> str:
    """Devuelve el punto de montaje del sistema de ficheros que contiene `path`.

    Sube por los directorios padre hasta encontrar uno que sea punto de montaje.
    Funciona aunque `path` todavía no exista (usa el ancestro existente).
    """
    p = os.path.abspath(path)
    while not os.path.ismount(p):
        parent = os.path.dirname(p)
        if parent == p:  # llegamos a la raíz
            return p
        p = parent
    return p


def requires_mount(path: str) -> bool:
    """True si `path` debe residir en un punto de montaje externo (USB).

    En Windows (desarrollo) nunca se exige. En Linux, se exige si la ruta cuelga
    de alguno de los directorios de montaje configurados (/media, /mnt)."""
    if _is_windows() or not _REQUIRE_MOUNT:
        return False
    ap = os.path.abspath(path)
    return any(ap == root or ap.startswith(root + os.sep) for root in _MOUNT_ROOTS)


def is_mounted(path: str) -> bool:
    """True si la ruta está sobre un punto de montaje real.

    Para rutas que requieren montaje (USB), comprueba que exista un mountpoint
    ancestro DENTRO del árbol de montaje (p.ej. /media/usb), no la raíz `/`.
    Para rutas que no requieren montaje, siempre True."""
    if not requires_mount(path):
        return True
    mp = find_mountpoint(path)
    # El mountpoint debe ser un subdirectorio real de /media o /mnt (p.ej.
    # /media/usb). Si acaba en "/" o en el propio /media, el USB no está montado.
    return any(mp.startswith(root + os.sep) for root in _MOUNT_ROOTS)


def _default_path(key: str) -> str:
    """Valor por defecto según el SO. En Linux (Raspberry) todo al USB salvo logs."""
    if _is_windows():
        base = "C:/PoC/sante_data"
        defaults = {
            KEY_SIGNED_DOCS: f"{base}/documentos_firmados",
            KEY_INVOICES: f"{base}/facturas",
            KEY_PATIENT_DOCS: f"{base}/pacientes",
            KEY_AUTO_BACKUP: f"{base}/backups",
        }
    else:
        defaults = {
            KEY_SIGNED_DOCS: "/media/usb/documentos_firmados",
            KEY_INVOICES: "/media/usb/facturas",
            KEY_PATIENT_DOCS: "/media/usb/pacientes",
            KEY_AUTO_BACKUP: "/media/usb/backups",
        }
    return defaults[key]


# =====================================================================
# Resolución de rutas base
# =====================================================================

def resolve_base_path(db: Session, key: str) -> str:
    """Resuelve la ruta base configurada (Config -> env -> default por SO),
    SIN comprobar montaje ni crear directorios."""
    if key not in STORAGE_KEYS:
        raise ValueError(f"Clave de almacenamiento desconocida: {key}")
    row = db.query(Config).filter(Config.key == key).first()
    value = (row.value.strip() if row and row.value else "") or ""
    if not value:
        value = os.getenv(_ENV_VAR[key], "").strip()
    if not value:
        value = _default_path(key)
    return value


def get_base_path(db: Session, key: str, *, ensure: bool = True, check_mount: bool = True) -> str:
    """Devuelve la ruta base de una categoría.

    - `check_mount` (por defecto True): si la ruta debe estar en un USB y su punto
      de montaje NO está activo, lanza StorageUnavailableError y NO crea nada.
      Así nunca se escribe en la SD por error. Poner a False para consultas de
      estado o lecturas que no deban fallar.
    - `ensure` (por defecto True): crea el directorio si no existe (solo tras
      pasar la comprobación de montaje).
    """
    value = resolve_base_path(db, key)

    if check_mount and requires_mount(value) and not is_mounted(value):
        raise StorageUnavailableError(
            f"El almacenamiento externo (USB) no está disponible: '{value}' no está "
            f"montado. No se guardará nada para evitar escribir en la tarjeta SD."
        )

    if ensure:
        os.makedirs(value, exist_ok=True)
    return value


def set_base_path(db: Session, key: str, value: str) -> None:
    """Guarda la ruta base de una categoría en la tabla Config (no hace commit)."""
    if key not in STORAGE_KEYS:
        raise ValueError(f"Clave de almacenamiento desconocida: {key}")
    value = (value or "").strip()
    row = db.query(Config).filter(Config.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))


def get_all_base_paths(db: Session, *, ensure: bool = False) -> dict[str, str]:
    """Devuelve todas las rutas base configuradas, indexadas por clave.
    No comprueba montaje (uso informativo)."""
    return {key: resolve_base_path(db, key) for key in STORAGE_KEYS}


# Atajos por categoría. Por defecto exigen que el USB esté montado (check_mount=True)
# y crean el directorio. Para lecturas/estado que no deban fallar, pasar
# check_mount=False y ensure=False.
def get_signed_docs_path(db: Session, *, ensure: bool = True, check_mount: bool = True) -> str:
    return get_base_path(db, KEY_SIGNED_DOCS, ensure=ensure, check_mount=check_mount)


def get_invoices_path(db: Session, *, ensure: bool = True, check_mount: bool = True) -> str:
    return get_base_path(db, KEY_INVOICES, ensure=ensure, check_mount=check_mount)


def get_patient_docs_path(db: Session, *, ensure: bool = True, check_mount: bool = True) -> str:
    return get_base_path(db, KEY_PATIENT_DOCS, ensure=ensure, check_mount=check_mount)


def get_auto_backup_path(db: Session, *, ensure: bool = True, check_mount: bool = True) -> str:
    return get_base_path(db, KEY_AUTO_BACKUP, ensure=ensure, check_mount=check_mount)


# =====================================================================
# Nombres únicos globales y reconstrucción de rutas absolutas
# =====================================================================

def unique_name(base_name: str, ext: str = "") -> str:
    """Devuelve un nombre de fichero único a nivel global.

    Antepone un identificador aleatorio corto (8 hex) al nombre indicado, de forma
    que dos ficheros con el mismo nombre lógico nunca colisionen aunque acaben en
    la misma carpeta tras fusionar categorías.

    Ejemplos:
        unique_name("F-2026-0001", ".pdf") -> "a1b2c3d4_F-2026-0001.pdf"
        unique_name("informe.pdf")          -> "a1b2c3d4_informe.pdf"
    """
    short = uuid.uuid4().hex[:8]
    if ext and not ext.startswith("."):
        ext = "." + ext
    safe_base = (base_name or "").strip().replace(os.sep, "_").replace("/", "_")
    return f"{short}_{safe_base}{ext}"


def abs_path(base_path: str, relative_name: str) -> str:
    """Reconstruye la ruta absoluta de un fichero: base + nombre relativo."""
    return os.path.join(base_path, relative_name)


# =====================================================================
# Utilidades de disco
# =====================================================================

def free_space_bytes(path: str) -> int:
    """Espacio libre (bytes) en el sistema de ficheros que contiene `path`.

    Sube por los directorios padre hasta encontrar uno existente, porque la ruta
    concreta puede no existir todavía.
    """
    probe = path
    while probe and not os.path.exists(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    if not probe or not os.path.exists(probe):
        return 0
    return shutil.disk_usage(probe).free


def dir_total_size(path: str) -> int:
    """Tamaño total (bytes) de todos los ficheros directamente dentro de `path`."""
    total = 0
    if not os.path.isdir(path):
        return 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def list_files(path: str) -> list[str]:
    """Nombres de ficheros (no directorios) directamente dentro de `path`."""
    if not os.path.isdir(path):
        return []
    return [e.name for e in os.scandir(path) if e.is_file()]


# =====================================================================
# Movimiento seguro de ficheros entre carpetas
# =====================================================================

@dataclass
class MovePlan:
    """Resultado del análisis previo a un movimiento de carpeta."""
    src: str
    dst: str
    files: list[str] = field(default_factory=list)   # ficheros a mover
    total_bytes: int = 0
    free_bytes: int = 0
    collisions: list[str] = field(default_factory=list)  # nombres ya presentes en dst
    ok: bool = True
    reason: str = ""

    @property
    def count(self) -> int:
        return len(self.files)


def plan_move(src: str, dst: str, *, margin: float = 0.10) -> MovePlan:
    """Analiza un movimiento src -> dst sin tocar nada.

    Comprueba:
      - Si origen y destino son la misma carpeta (no hay nada que hacer).
      - Colisiones de nombre en destino (requieren intervención manual).
      - Espacio libre en destino (tamaño origen + margen).
    """
    plan = MovePlan(src=os.path.abspath(src), dst=os.path.abspath(dst))

    if plan.src == plan.dst:
        plan.ok = True
        plan.reason = "same"
        return plan

    plan.files = list_files(src)
    plan.total_bytes = dir_total_size(src)
    plan.free_bytes = free_space_bytes(dst)

    if not plan.files:
        plan.ok = True
        plan.reason = "empty"
        return plan

    # Colisiones: nombres que ya existen en destino.
    existing = set(list_files(dst))
    plan.collisions = sorted(n for n in plan.files if n in existing)
    if plan.collisions:
        plan.ok = False
        plan.reason = "collision"
        return plan

    # Espacio: necesitamos el tamaño total más un margen de seguridad.
    needed = int(plan.total_bytes * (1 + margin))
    if plan.free_bytes < needed:
        plan.ok = False
        plan.reason = "no_space"
        return plan

    plan.ok = True
    plan.reason = "ready"
    return plan


def execute_move(src: str, dst: str, plan: MovePlan, progress_cb=None) -> None:
    """Mueve los ficheros de src a dst de forma segura (copiar-verificar-borrar).

    Estrategia: por cada fichero, se COPIA a destino y se verifica que el tamaño
    en bytes coincide. Solo cuando TODOS los ficheros se han copiado y verificado
    se borran del origen. Si algo falla, se limpia lo copiado a medias y se lanza
    excepción; el origen queda intacto (sigue siendo la fuente de verdad).

    `progress_cb(done, total, current_name)` se llama tras cada fichero copiado,
    si se proporciona.
    """
    if plan.reason in ("same", "empty"):
        return
    if not plan.ok:
        raise RuntimeError(f"El plan de movimiento no es válido: {plan.reason}")

    os.makedirs(dst, exist_ok=True)
    copied: list[str] = []
    total = len(plan.files)

    try:
        for i, name in enumerate(plan.files, start=1):
            src_file = os.path.join(src, name)
            dst_file = os.path.join(dst, name)
            if not os.path.isfile(src_file):
                # El fichero desapareció durante el proceso: abortar.
                raise RuntimeError(f"El fichero de origen desapareció: {name}")
            shutil.copy2(src_file, dst_file)
            # Verificación por tamaño de bytes (detecta copias truncadas).
            if os.path.getsize(dst_file) != os.path.getsize(src_file):
                raise RuntimeError(f"Copia incompleta verificando: {name}")
            copied.append(dst_file)
            if progress_cb:
                progress_cb(i, total, name)

        # Verificación final: todos los ficheros presentes en destino.
        for name in plan.files:
            if not os.path.isfile(os.path.join(dst, name)):
                raise RuntimeError(f"Falta en destino tras copiar: {name}")

    except Exception:
        # Rollback: borrar lo copiado a destino; el origen no se ha tocado.
        for f in copied:
            try:
                os.remove(f)
            except OSError:
                pass
        raise

    # Todo verificado: ahora sí, borrar el origen.
    for name in plan.files:
        try:
            os.remove(os.path.join(src, name))
        except OSError:
            pass
