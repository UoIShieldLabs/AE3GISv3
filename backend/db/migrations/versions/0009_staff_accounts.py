"""Several staff accounts: admins and instructors, each with a class.

Before this there was one instructor (from the environment), one class whose
join code and sign-up switch lived in ``app_settings``, and ``owner_id`` NULL
meant "the instructor's". Now:

- ``users.role`` is ``admin`` | ``instructor`` | ``student``; ``env_managed``
  marks the admin whose password is the environment's, and
  ``must_change_password`` a temporary password;
- ``classes`` holds each staff member's join code and sign-up switch (one per
  staff member for now: ``instructor_id`` is unique), and a student's
  ``users.class_id`` names theirs;
- every topology has an owner.

Upgrading an instance with accounts on: the instructor row becomes the
environment's admin, gets a class with the old join code and switch, every
student joins it, and the topologies without an owner become that admin's.
With accounts off there are no rows; ``services.accounts.bootstrap_admin`` does
the same adoption when accounts are first turned on.

``users.class_id`` is a plain ``ADD COLUMN`` without a foreign key, so the
users table is never rebuilt (the sessions' ``ON DELETE CASCADE`` points at
it); the services keep it consistent.

Revision ID: 0009_staff_accounts
Revises: 0008_topology_retired
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0009_staff_accounts"
down_revision = "0008_topology_retired"
branch_labels = None
depends_on = None

_OLD_KEYS = ("class.join_code", "class.signup_open")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "classes" not in set(inspector.get_table_names()):
        op.create_table(
            "classes",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "instructor_id",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("join_code", sa.String(), nullable=True, unique=True),
            sa.Column("signup_open", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    columns = {c["name"] for c in inspector.get_columns("users")}
    if "class_id" not in columns:
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("class_id", sa.String(), nullable=True))
            batch.add_column(
                sa.Column("env_managed", sa.Boolean(), nullable=False, server_default=sa.false())
            )
            batch.add_column(
                sa.Column(
                    "must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()
                )
            )
    indexes = {i["name"] for i in sa.inspect(bind).get_indexes("users")}
    if "ix_users_class_id" not in indexes:
        op.create_index("ix_users_class_id", "users", ["class_id"])

    _adopt_the_old_instructor(bind)


def _adopt_the_old_instructor(bind) -> None:
    users = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("role", sa.String),
        sa.column("class_id", sa.String),
        sa.column("env_managed", sa.Boolean),
    )
    classes = sa.table(
        "classes",
        sa.column("id", sa.String),
        sa.column("instructor_id", sa.String),
        sa.column("join_code", sa.String),
        sa.column("signup_open", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    settings = sa.table("app_settings", sa.column("key", sa.String), sa.column("value", sa.JSON))
    topologies = sa.table("topologies", sa.column("owner_id", sa.String))

    if bind.execute(sa.select(users.c.id).where(users.c.env_managed.is_(True))).first():
        return  # already done
    row = bind.execute(sa.select(users.c.id).where(users.c.role == "instructor")).first()
    if row is None:
        return  # accounts were never on
    admin_id = row[0]
    old = dict(
        bind.execute(
            sa.select(settings.c.key, settings.c.value).where(settings.c.key.in_(_OLD_KEYS))
        ).all()
    )

    bind.execute(
        sa.update(users).where(users.c.id == admin_id).values(role="admin", env_managed=True)
    )
    class_id = bind.execute(
        sa.select(classes.c.id).where(classes.c.instructor_id == admin_id)
    ).scalar()
    if class_id is None:
        class_id = uuid.uuid4().hex
        bind.execute(
            sa.insert(classes).values(
                id=class_id,
                instructor_id=admin_id,
                join_code=old.get("class.join_code") or None,
                signup_open=bool(old.get("class.signup_open")),
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
    bind.execute(
        sa.update(users)
        .where(users.c.role == "student", users.c.class_id.is_(None))
        .values(class_id=class_id)
    )
    bind.execute(
        sa.update(topologies).where(topologies.c.owner_id.is_(None)).values(owner_id=admin_id)
    )
    bind.execute(sa.delete(settings).where(settings.c.key.in_(_OLD_KEYS)))


def downgrade() -> None:
    op.drop_index("ix_users_class_id", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("must_change_password")
        batch.drop_column("env_managed")
        batch.drop_column("class_id")
    op.drop_table("classes")
