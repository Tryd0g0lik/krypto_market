"""
alembic/env.py
"""

import logging
import re
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from cryptomarket.project.settings.core import DEBUG, settings
from cryptomarket.project.settings.settings_env import PROJECT_MODE_

project_dir = str(Path(__file__).parent.parent.absolute())
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)
    print(f"Added {project_dir} to sys.path")
    logging.log(0, f"Added {project_dir} to sys.path")

www_src = "/www/src"
if www_src not in sys.path:
    sys.path.insert(0, www_src)
    print(f"Added {www_src} to sys.path")
    logging.log(0, f"Added {www_src} to sys.path")


try:
    from cryptomarket.models.model_base import target_metadata

    print("Successfully imported target_metadata")
    logging.log(0, "Successfully imported target_metadata")

except ImportError as e:
    print(f"Import error: {e}")
    logging.log(0, f"Import error: {e}")
    print(f"Current sys.path: {sys.path}")
    logging.log(0, f"Current sys.path: {sys.path}")
    import cryptomarket

    print(f"cryptomarket module found at: {cryptomarket.__file__}")
    raise

setting = settings()


BASE_DIR = Path(__file__).parent.parent.absolute()

sys.path.insert(0, str(BASE_DIR))


def get_sync_postres_url():
    """Возвращает синхронный URL для PostgreSQL, убирая +asyncpg"""
    async_url = setting.get_database_url_external
    # postgresql+asyncpg://... на postgresql://...
    sync_url = re.sub(r"postgresql\+asyncpg", "postgresql", async_url)
    keepalive_params = (
        "?keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=5"
    )
    if "?" in sync_url:
        sync_url = f"{sync_url}&{keepalive_params.lstrip('?')}"
    else:
        sync_url = f"{sync_url}{keepalive_params}"
    return sync_url


def get_sync_sqlit_url():
    return "sqlite:///cryptomarket/cryptomarket_db.sqlit3"


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config


# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    Запуск миграций в offline-режиме."""
    url = get_sync_sqlit_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Запуск миграций с соединением."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # важно для SQLite
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section)
    url = get_sync_sqlit_url()

    if url:
        configuration["sqlalchemy.url"] = url

    # async engine
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section) or {}

    if not DEBUG and PROJECT_MODE_ == "production":
        configuration["sqlalchemy.url"] = get_sync_postres_url()
    else:
        configuration["sqlalchemy.url"] = get_sync_sqlit_url()
    for key in ["version"]:
        if key in configuration:
            del configuration[key]

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        is_sqlite = connectable.dialect.name == "sqlite"
        include_schemas = connectable.dialect.name == "postgresql"

        include_schemas = not is_sqlite
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,
            include_schemas=include_schemas,  # Важно!
            version_table_schema=(
                None if is_sqlite else "crypto" if include_schemas else "alembic"
            ),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
