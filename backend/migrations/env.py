from __future__ import annotations

import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool
from backend.app.core.database import Base, configured_engine, normalize_database_url
from backend.app.models import entities  # noqa: F401 - register all mapped tables

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url") or "sqlite:///./astradeploy.db"
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=normalize_database_url(database_url), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = configured_engine(database_url, poolclass=pool.NullPool, future=True)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
