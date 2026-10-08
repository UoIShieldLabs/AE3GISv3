"""Add the registries table (Docker Hub namespaces whose images join the catalog).

Revision ID: 0005_registries
Revises: 0004_job_result
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_registries"
down_revision = "0004_job_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "registries" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "registries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False, server_default="dockerhub"),
        sa.Column("namespace", sa.String(), nullable=False, unique=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("registries")
