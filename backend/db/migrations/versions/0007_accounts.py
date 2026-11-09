"""Accounts: users, sessions, app settings; topology owner / publish / source.

Classroom mode (``AE3GIS_INSTRUCTOR_PASSWORD``) has one instructor and
self-registered students. A topology's ``owner_id`` is the student who owns it,
NULL for the instructor (every row older than this migration, benchmark and
generated topologies, anything made in open mode). ``published`` makes an
instructor topology visible to students; ``source_id``/``source_version`` mark a
student's copy of a published topology and the source version it was taken from.

The topology columns are plain ``ADD COLUMN``s without foreign keys, so the
table is never rebuilt (the jobs table's ``ON DELETE CASCADE`` points at it);
the services keep them consistent, as they do for ``events.topology_id``.

Revision ID: 0007_accounts
Revises: 0006_topology_saved_state
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_accounts"
down_revision = "0006_topology_saved_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("username", sa.String(), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        )
    if "sessions" not in tables:
        op.create_table(
            "sessions",
            sa.Column("token_hash", sa.String(), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    if "app_settings" not in tables:
        op.create_table(
            "app_settings",
            sa.Column("key", sa.String(), primary_key=True),
            sa.Column("value", sa.JSON(), nullable=True),
        )

    columns = {c["name"] for c in inspector.get_columns("topologies")}
    if "owner_id" not in columns:
        with op.batch_alter_table("topologies") as batch:
            batch.add_column(sa.Column("owner_id", sa.String(), nullable=True))
            batch.add_column(
                sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false())
            )
            batch.add_column(sa.Column("source_id", sa.String(), nullable=True))
            batch.add_column(sa.Column("source_version", sa.Integer(), nullable=True))
    indexes = {i["name"] for i in sa.inspect(bind).get_indexes("topologies")}
    if "ix_topologies_owner_id" not in indexes:
        op.create_index("ix_topologies_owner_id", "topologies", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_topologies_owner_id", table_name="topologies")
    with op.batch_alter_table("topologies") as batch:
        batch.drop_column("source_version")
        batch.drop_column("source_id")
        batch.drop_column("published")
        batch.drop_column("owner_id")
    op.drop_table("app_settings")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
