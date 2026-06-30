"""Alembic env.py — Configuración de migraciones."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Añade el directorio raíz al path para importar los modelos
sys.path.insert(0, str(Path(__file__).parent.parent))

from quote_engine.db.base import Base
from quote_engine.db import models  # noqa: F401 — importar para que los modelos se registren

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url() -> str:
    """Obtiene la URL desde variables de entorno (prioridad) o alembic.ini."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "eon")
    password = os.getenv("POSTGRES_PASSWORD", "eon_dev_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5435")
    db = os.getenv("POSTGRES_DB", "eon_index_clima")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    """Corre migraciones en modo 'offline' (genera SQL sin conectar)."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Corre migraciones conectando a la base de datos."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
