"""The agent: chats and their messages, the class tutor switch, API tokens.

- ``agent_chats`` / ``agent_messages``: a user's conversations with the agent
  (messages append-only, ``(chat_id, seq)`` unique);
- ``classes.tutor_enabled``: whether a class's students get the read-only tutor
  (off by default);
- ``sessions.purpose`` (``browser`` | ``api``) and ``sessions.label``: tokens a
  user makes for an external agent (MCP) live beside browser sessions.

Columns are plain ``ADD COLUMN``s (no table rebuild), like 0009.

Revision ID: 0010_agent
Revises: 0009_staff_accounts
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_agent"
down_revision = "0009_staff_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "agent_chats" not in tables:
        op.create_table(
            "agent_chats",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "owner_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
            ),
            sa.Column(
                "topology_id",
                sa.String(),
                sa.ForeignKey("topologies.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("mode", sa.String(), nullable=False),
            sa.Column("auto_approve", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("last_job_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_agent_chats_owner_id", "agent_chats", ["owner_id"])
        op.create_index("ix_agent_chats_topology_id", "agent_chats", ["topology_id"])

    if "agent_messages" not in tables:
        op.create_table(
            "agent_messages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "chat_id",
                sa.String(),
                sa.ForeignKey("agent_chats.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("seq", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("content", sa.JSON(), nullable=False),
            sa.Column("provider_raw", sa.JSON(), nullable=True),
            sa.Column("job_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_agent_messages_chat_seq", "agent_messages", ["chat_id", "seq"], unique=True
        )

    if "tutor_enabled" not in {c["name"] for c in inspector.get_columns("classes")}:
        op.add_column(
            "classes",
            sa.Column("tutor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    session_columns = {c["name"] for c in inspector.get_columns("sessions")}
    if "purpose" not in session_columns:
        op.add_column(
            "sessions",
            sa.Column("purpose", sa.String(), nullable=False, server_default="browser"),
        )
    if "label" not in session_columns:
        op.add_column("sessions", sa.Column("label", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_agent_messages_chat_seq", table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_index("ix_agent_chats_topology_id", table_name="agent_chats")
    op.drop_index("ix_agent_chats_owner_id", table_name="agent_chats")
    op.drop_table("agent_chats")
    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("label")
        batch.drop_column("purpose")
    with op.batch_alter_table("classes") as batch:
        batch.drop_column("tutor_enabled")
