"""Runner de migraciones ligeras para SQLite.

Aplica de forma incremental los scripts de migración que aún no se hayan
ejecutado, registrándolos en la tabla `schema_migrations`. Es idempotente:
ejecutarlo varias veces no vuelve a aplicar migraciones ya aplicadas.

Cada migración es un módulo Python dentro de `migrations/versions/` cuyo nombre
empieza por un número de orden, por ejemplo:

    migrations/versions/0001_add_consent_date.py

y expone una función `upgrade(connection)` que recibe una conexión SQLAlchemy
y realiza los cambios (idealmente idempotentes y no destructivos).

Uso:
    python -m migrations.runner            # aplica las pendientes
    python -m migrations.runner --status   # muestra estado sin aplicar nada
"""
import argparse
import importlib.util
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import text

# Permite importar app.* cuando se ejecuta desde la raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine  # noqa: E402

VERSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "versions")


def _ensure_migrations_table(conn):
    conn.execute(text(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL"
        ")"
    ))


def _applied_versions(conn) -> set:
    rows = conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
    return {r[0] for r in rows}


def _discover_migrations() -> list:
    """Devuelve lista ordenada de (version, ruta) de los scripts disponibles."""
    if not os.path.isdir(VERSIONS_DIR):
        return []
    files = [
        f for f in os.listdir(VERSIONS_DIR)
        if f.endswith(".py") and not f.startswith("__")
    ]
    return sorted((f[:-3], os.path.join(VERSIONS_DIR, f)) for f in files)


def _load_upgrade(version: str, path: str):
    spec = importlib.util.spec_from_file_location(f"migrations.versions.{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "upgrade"):
        raise RuntimeError(f"La migración {version} no define upgrade(connection)")
    return module.upgrade


def status() -> int:
    """Muestra qué migraciones están aplicadas y cuáles pendientes."""
    with engine.begin() as conn:
        _ensure_migrations_table(conn)
        applied = _applied_versions(conn)
    migrations = _discover_migrations()
    if not migrations:
        print("No hay migraciones definidas.")
        return 0
    pending = [v for v, _ in migrations if v not in applied]
    print(f"Migraciones totales: {len(migrations)} | aplicadas: {len(applied)} | pendientes: {len(pending)}")
    for version, _ in migrations:
        mark = "[x]" if version in applied else "[ ]"
        print(f"  {mark} {version}")
    return len(pending)


def run() -> int:
    """Aplica las migraciones pendientes en orden. Devuelve nº aplicadas."""
    migrations = _discover_migrations()
    applied_count = 0
    with engine.begin() as conn:
        _ensure_migrations_table(conn)
        applied = _applied_versions(conn)
        for version, path in migrations:
            if version in applied:
                continue
            print(f"Aplicando migración {version}...")
            upgrade = _load_upgrade(version, path)
            upgrade(conn)
            conn.execute(
                text("INSERT INTO schema_migrations (version, applied_at) VALUES (:v, :t)"),
                {"v": version, "t": datetime.now(timezone.utc).isoformat()},
            )
            applied_count += 1
    if applied_count == 0:
        print("No hay migraciones pendientes.")
    else:
        print(f"Aplicadas {applied_count} migracion(es).")
    return applied_count


def main():
    parser = argparse.ArgumentParser(description="Runner de migraciones de Santé")
    parser.add_argument("--status", action="store_true", help="Solo mostrar estado")
    args = parser.parse_args()
    if args.status:
        status()
    else:
        run()


if __name__ == "__main__":
    main()
