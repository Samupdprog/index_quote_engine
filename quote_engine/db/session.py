"""Configuración de sesión SQLAlchemy.

Lee DATABASE_URL desde variables de entorno o construye la URL
a partir de POSTGRES_* variables. Si no hay DB configurada,
devuelve None y la app funciona en modo sin-DB (sin catálogo).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def _build_database_url() -> str | None:
    """Construye la URL de conexión a partir de variables de entorno."""
    # Prioridad: DATABASE_URL explícita
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Construir desde partes
    user = os.getenv("POSTGRES_USER", "eon")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5435")
    db = os.getenv("POSTGRES_DB", "eon_index_clima")

    if not password:
        return None  # Sin contraseña, no intentar conectar

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@lru_cache(maxsize=1)
def _get_engine():
    """Crea el engine SQLAlchemy (singleton)."""
    url = _build_database_url()
    if url is None:
        return None

    return create_engine(
        url,
        pool_pre_ping=True,        # Detecta conexiones muertas
        pool_size=5,
        max_overflow=10,
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
    )


def get_engine():
    """Devuelve el engine SQLAlchemy o None si no hay DB configurada."""
    return _get_engine()


def get_session_factory():
    """Devuelve SessionFactory o None."""
    engine = get_engine()
    if engine is None:
        return None
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency injection para FastAPI: yield session y cierra al final."""
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError(
            "Base de datos no configurada. "
            "Copia .env.example como .env y configura POSTGRES_PASSWORD."
        )
    db = factory()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> dict:
    """Verifica la conexión a la base de datos. Devuelve dict con estado."""
    engine = get_engine()
    if engine is None:
        return {"ok": False, "error": "DATABASE_URL no configurada"}

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
        return {"ok": True, "version": version}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def is_db_available() -> bool:
    """True si la DB está configurada y accesible."""
    return check_connection()["ok"]
