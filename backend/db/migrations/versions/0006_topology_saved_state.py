"""Add topologies.saved_state (per-node snapshot images from "save & destroy").

Revision ID: 0006_topology_saved_state
Revises: 0005_registries
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_topology_saved_state"
down_revision = "0005_registries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("topologies")}
    if "saved_state" in columns:
        return
    with op.batch_alter_table("topologies") as batch:
        batch.add_column(sa.Column("saved_state", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("topologies") as batch:
        batch.drop_column("saved_state")
