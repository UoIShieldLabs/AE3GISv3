import sqlalchemy as sa
from alembic import command

from db.migrations import alembic_config


def _rows(conn, sql):
    return [tuple(r) for r in conn.execute(sa.text(sql))]


def test_0003_keeps_jobs_and_allows_jobs_without_a_topology(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "0002_jobs_events_version")
    engine = sa.create_engine(url)
    with engine.begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO topologies (id, name, data, status, version) "
                "VALUES ('t1', 'T', '{}', 'idle', 1), ('t2', 'U', '{}', 'idle', 1)"
            )
        )
        c.execute(
            sa.text(
                "INSERT INTO jobs (id, topology_id, kind, status, steps, created_at) VALUES "
                "('j1', 't1', 'deploy', 'succeeded', '[]', CURRENT_TIMESTAMP), "
                "('j2', 't1', 'deploy', 'running', '[]', CURRENT_TIMESTAMP), "
                "('j3', 't2', 'destroy', 'failed', '[]', CURRENT_TIMESTAMP)"
            )
        )

    command.upgrade(cfg, "head")

    with engine.begin() as c:
        assert _rows(c, "SELECT id, subject, status FROM jobs ORDER BY id") == [
            ("j1", "topology:t1", "succeeded"),
            ("j2", "topology:t1", "failed"),  # nothing survives a restart
            ("j3", "topology:t2", "failed"),
        ]
        c.execute(
            sa.text(
                "INSERT INTO jobs (id, topology_id, subject, kind, status, steps, created_at) "
                "VALUES ('j4', NULL, 'image:x', 'build', 'queued', '[]', CURRENT_TIMESTAMP)"
            )
        )

    # The ON DELETE CASCADE survived the table rebuild.
    with engine.connect() as c:
        c.exec_driver_sql("PRAGMA foreign_keys=ON")
        c.execute(sa.text("DELETE FROM topologies WHERE id = 't1'"))
        c.commit()
        assert _rows(c, "SELECT id FROM jobs ORDER BY id") == [("j3",), ("j4",)]

    # Running it again is a no-op.
    command.upgrade(cfg, "head")


def test_0004_adds_a_result_column_and_keeps_the_cascade(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "0003_job_subject")
    engine = sa.create_engine(url)
    with engine.begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO topologies (id, name, data, status, version) "
                "VALUES ('t1', 'T', '{}', 'idle', 1)"
            )
        )
        c.execute(
            sa.text(
                "INSERT INTO jobs (id, topology_id, subject, kind, status, steps, created_at) "
                "VALUES ('j1', 't1', 'topology:t1', 'deploy', 'succeeded', '[]', "
                "CURRENT_TIMESTAMP)"
            )
        )

    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")  # idempotent

    with engine.connect() as c:
        assert _rows(c, "SELECT id, result FROM jobs") == [("j1", None)]
        c.exec_driver_sql("PRAGMA foreign_keys=ON")
        c.execute(sa.text("DELETE FROM topologies WHERE id = 't1'"))
        c.commit()
        assert _rows(c, "SELECT id FROM jobs") == []
