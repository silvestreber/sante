"""Configuración de la conexión a la base de datos SQLite.

Usa SQLAlchemy como ORM. La BD se almacena en `sante.db` en la raíz del proyecto.

Características especiales:
    - Se registra la función SQL `unaccent` en cada conexión SQLite para permitir
      búsquedas insensibles a tildes (ej: "perez" encuentra "Pérez").
    - `get_db()` es la dependencia FastAPI estándar para inyectar una sesión de BD
      en los endpoints; garantiza que la sesión se cierra al terminar la petición.

Uso en endpoints:
    def mi_endpoint(db: Session = Depends(get_db)):
        ...
"""
import unicodedata

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./sante.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _strip_accents(value):
    """Quita las tildes/diacríticos de un texto (para búsquedas insensibles a acentos).
    Devuelve None si la entrada es None."""
    if value is None:
        return None
    text = str(value)
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")


@event.listens_for(engine, "connect")
def _register_sqlite_functions(dbapi_connection, connection_record):
    """Registra la función SQL `unaccent` en cada conexión SQLite, para poder
    comparar ignorando las tildes desde las consultas."""
    dbapi_connection.create_function("unaccent", 1, _strip_accents)


def get_db():
    """Dependencia FastAPI que proporciona una sesión de BD por petición.

    Abre una sesión, la cede al endpoint y la cierra al finalizar (incluso si
    hay una excepción). Uso: `db: Session = Depends(get_db)`.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
