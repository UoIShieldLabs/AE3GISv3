"""Jobs that are not tied to a topology: nullable topology_id, a subject key, params.

A job's *subject* is what it serialises on: ``topology:<id>`` for deploy and
destroy, ``image:<ref>`` for an image build, ``source:<name>`` for a source
sync. Existing rows are backfilled with their topology subject. ``params``
holds a job's inputs (e.g. the image ref and whether to build without cache).

SQLite cannot ALTER a column's nullability, so the table is recreated. The
0002 shape is spelled out as ``copy_from`` rather than reflected so the
``ON DELETE CASCADE`` foreign key survives the copy.

Revision ID: 0003_job_subject
Revises: 0002_jobs_events_version
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_job_subject"
down_revision = "0002_jobs_events_version"
branch_labels = None
depends_on = None


def _jobs_0002() -> sa.Table:
    return sa.Table(
        "jobs",
        sa.MetaData(),
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
        sa.Index("ix_jobs_topology_created", "topology_id", "created_at"),
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("jobs")}
    if "subject" in columns:
        return

    # Nothing survives a migration (it only runs at startup): close out leftovers
    # before the copy so no row is carried over as "running".
    bind.execute(
        sa.text(
            "UPDATE jobs SET status = 'failed', "
            "error = 'Server restarted while the job was running', "
            "finished_at = CURRENT_TIMESTAMP "
            "WHERE status IN ('queued', 'running')"
        )
    )

    with op.batch_alter_table("jobs", recreate="always", copy_from=_jobs_0002()) as batch:
        batch.alter_column("topology_id", existing_type=sa.String(), nullable=True)
        batch.add_column(sa.Column("subject", sa.String(), nullable=True))
        batch.add_column(sa.Column("params", sa.JSON(), nullable=True))

    bind.execute(
        sa.text(
            "UPDATE jobs SET subject = 'topology:' || topology_id "
            "WHERE subject IS NULL AND topology_id IS NOT NULL"
        )
    )
    op.create_index("ix_jobs_subject_created", "jobs", ["subject", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_subject_created", table_name="jobs")
    op.execute("DELETE FROM jobs WHERE topology_id IS NULL")
    with op.batch_alter_table("jobs", recreate="always") as batch:
        batch.drop_column("params")
        batch.drop_column("subject")
        batch.alter_column("topology_id", existing_type=sa.String(), nullable=False)
