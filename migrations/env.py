"""
migrations/env.py — Configuração do Alembic para o OrbisClin.
Lê DATABASE_URL do .env via config.py e importa os modelos para autogenerate.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Garante que a raiz do projeto está no path para imports app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.database import Base

# Importa todos os modelos para que o autogenerate os detecte
import app.core.models  # noqa: F401

settings = get_settings()

# Alembic Config
config = context.config

# Injeta a DATABASE_URL do .env — sobrescreve o sqlalchemy.url do alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configura logging se o alembic.ini tiver seção [loggers]
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata dos modelos — necessário para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera SQL sem conexão ao banco (útil para revisar antes de aplicar)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # necessário para SQLite (ALTER TABLE)
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica migrations diretamente no banco."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # necessário para SQLite (ALTER TABLE)
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
