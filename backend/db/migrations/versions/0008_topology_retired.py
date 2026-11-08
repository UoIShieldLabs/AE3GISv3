"""topologies.retired_at: a student's lesson copy whose lesson was unpublished
or deleted. Hidden from everyone at once; its lab is destroyed and the row
deleted in the background (services.lessons).

Revision ID: 0008_topology_retired
Revises: 0007_accounts
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_topology_retired"
down_revision = "0007_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("topologies")}
    if "retired_at" in columns:
        return
    with op.batch_alter_table("topologies") as batch:
        batch.add_column(sa.Column("retired_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("topologies") as batch:
        batch.drop_column("retired_at")
