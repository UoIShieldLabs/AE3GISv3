"""Environment-driven configuration (pydantic-settings).

Every setting is read from an ``AE3GIS_`` environment variable. The app is
built from a ``Settings`` instance (see ``main.create_app``) so tests can pass
their own without touching the process environment.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

API_VERSION = "3.1.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AE3GIS_", extra="ignore")

    # Storage: the SQLite DB and any runtime data live under data_dir unless
    # db_path points elsewhere.
    data_dir: Path = BASE_DIR / "data"
    db_path: Path | None = None

    # Auth is OPT-IN. Empty (the default) leaves the API open: fine for a local
    # single-user lab, NOT for a shared or network-reachable host, since the API
    # creates and destroys containers. Set a token to require it on every REST
    # route and WebSocket upgrade.
    instructor_token: str = ""

    # Comma-separated origins, or "*" for any (dev default).
    cors_origins: str = "*"

    # Deployment engine: "kathara" (default) or "fake" (in-memory, for tests
    # and for running the UI without Docker).
    engine: str = "kathara"

    log_level: str = "INFO"

    # Job logs (build output etc.) are files under data_dir/job-logs.
    job_log_max_bytes: int = 8_000_000
    job_log_retention_days: float = 14

    # Image builds. Git sources are cloned under data_dir/sources. An override
    # (JSON: {"<source name>": "/path"}) points a source at a local checkout,
    # e.g. to iterate on Dockerfiles; in Docker the path must be mounted.
    max_concurrent_builds: int = 2
    source_overrides: dict[str, Path] = {}

    # Captures and traffic runs keep their output (pcaps, time series, run.json)
    # under data_dir/artifacts/<job id>/, deleted after the retention period.
    artifact_retention_days: float = 30
    capture_max_bytes: int = 256_000_000
    capture_max_seconds: int = 3600
    max_active_captures: int = 8
    # Packet summaries streamed to the browser per capture; the rest are counted.
    capture_ui_max_pps: int = 500
    traffic_max_seconds: int = 4 * 3600

    # Recorded with every capture and traffic run so results from different
    # machines and code versions can be told apart. ``host_label`` names the
    # real machine (Docker Desktop only reports its VM); ``git_commit`` is set
    # at image build time. ``instance_id`` tags the sidecars this backend
    # starts; empty = generated once and kept in data_dir/instance-id.
    host_label: str = ""
    git_commit: str = ""
    git_dirty: bool = False
    instance_id: str = ""
    # "dev" (compose: source mounted, uvicorn --reload) or "prod"; recorded too.
    mode: str = ""

    @property
    def database_url(self) -> str:
        path = self.db_path or (self.data_dir / "ae3gis.db")
        return f"sqlite:///{path}"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*" or not raw:
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def auth_required(self) -> bool:
        return bool(self.instructor_token.strip())

    @property
    def job_logs_dir(self) -> Path:
        return self.data_dir / "job-logs"

    @property
    def sources_dir(self) -> Path:
        return self.data_dir / "sources"

    @property
    def build_ctx_dir(self) -> Path:
        return self.data_dir / "build-ctx"

    @property
    def artifacts_dir(self) -> Path:
        return self.data_dir / "artifacts"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for d in (self.job_logs_dir, self.sources_dir, self.build_ctx_dir, self.artifacts_dir):
            d.mkdir(parents=True, exist_ok=True)
        if self.db_path:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_instance_id(self) -> str:
        """This backend's id (tags its sidecars), persisted across restarts."""
        if not self.instance_id:
            path = self.data_dir / "instance-id"
            try:
                self.instance_id = path.read_text().strip()
            except OSError:
                self.instance_id = ""
            if not self.instance_id:
                self.instance_id = uuid.uuid4().hex[:12]
                path.write_text(self.instance_id + "\n")
        return self.instance_id


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings (from the environment). Tests build their own."""
    return Settings()
