"""Baseline: the topologies table as it existed before migrations were introduced.

Databases created by the old ``create_all`` already have this table; the
migration is a no-op for them so existing data volumes upgrade in place.

Revision ID: 0001_baseline
Revises: None
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "topologies" in inspector.get_table_names():
        return
    op.create_table(
        "topologies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("engine_state", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="idle"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("topologies")
