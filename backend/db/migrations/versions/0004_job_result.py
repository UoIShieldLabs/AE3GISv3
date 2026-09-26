"""A job's result: what a capture or traffic run produced.

A plain ADD COLUMN; the table is not recreated, so the foreign key and indexes
from 0003 are untouched. Idempotent like the earlier revisions.

Revision ID: 0004_job_result
Revises: 0003_job_subject
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_job_result"
down_revision = "0003_job_subject"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("jobs")}
    if "result" in columns:
        return
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("result", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("result")
