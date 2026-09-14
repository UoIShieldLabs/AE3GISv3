"""Programmatic Alembic runner (``run_migrations``) plus the migration scripts."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

_HERE = Path(__file__).resolve().parent


def alembic_config(database_url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(_HERE))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def run_migrations(database_url: str) -> None:
    """Bring the database at ``database_url`` to the latest revision."""
    command.upgrade(alembic_config(database_url), "head")
