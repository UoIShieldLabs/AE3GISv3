"""Add topology.version, and the jobs and events tables.

Revision ID: 0002_jobs_events_version
Revises: 0001_baseline
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_jobs_events_version"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("topologies")}
    if "version" not in columns:
        with op.batch_alter_table("topologies") as batch:
            batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    tables = set(inspector.get_table_names())
    if "jobs" not in tables:
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "topology_id",
                sa.String(),
                sa.ForeignKey("topologies.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="queued"),
            sa.Column("steps", sa.JSON(), nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_jobs_topology_created", "jobs", ["topology_id", "created_at"])

    if "events" not in tables:
        op.create_table(
            "events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("topology_id", sa.String(), nullable=True),
            sa.Column("job_id", sa.String(), nullable=True),
            sa.Column("ts", sa.DateTime(), nullable=False),
            sa.Column("level", sa.String(), nullable=False, server_default="info"),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("data", sa.JSON(), nullable=True),
        )
        op.create_index("ix_events_topology_id", "events", ["topology_id"])


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("jobs")
    with op.batch_alter_table("topologies") as batch:
        batch.drop_column("version")
