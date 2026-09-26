"""Files a job produces (``<artifacts_dir>/<job_id>/<name>``).

Captures write their pcap here, traffic runs their time series and
``run.json``. Like job logs, bulk output stays out of SQLite; the job row keeps
a small ``result`` summary. Names are flat and validated so a request can never
address a file outside its job's directory.
"""

from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

CONTENT_TYPES = {
    ".pcap": "application/vnd.tcpdump.pcap",
    ".json": "application/json",
    ".ndjson": "application/x-ndjson",
    ".zip": "application/zip",
    ".log": "text/plain",
    ".txt": "text/plain",
}


@dataclass
class Artifact:
    name: str
    size: int
    modified_at: datetime
    content_type: str


def content_type(name: str) -> str:
    return CONTENT_TYPES.get(Path(name).suffix, "application/octet-stream")


class ArtifactStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def dir(self, job_id: str, *, create: bool = False) -> Path:
        # Job ids are server-generated hex; never let one address another directory.
        if not job_id.isalnum():
            raise ValueError(f"Invalid job id: {job_id!r}")
        d = self.directory / job_id
        if create:
            d.mkdir(parents=True, exist_ok=True)
        return d

    def path(self, job_id: str, name: str, *, create_dir: bool = False) -> Path:
        if not _NAME.match(name) or ".." in name:
            raise ValueError(f"Invalid artifact name: {name!r}")
        return self.dir(job_id, create=create_dir) / name

    def list(self, job_id: str) -> list[Artifact]:
        d = self.dir(job_id)
        if not d.is_dir():
            return []
        out = []
        for p in sorted(d.iterdir()):
            if not p.is_file() or not _NAME.match(p.name):
                continue
            st = p.stat()
            out.append(
                Artifact(
                    name=p.name,
                    size=st.st_size,
                    modified_at=datetime.fromtimestamp(st.st_mtime, UTC),
                    content_type=content_type(p.name),
                )
            )
        return out

    def gc(self, retention_days: float, *, keep: set[str] | frozenset[str] = frozenset()) -> int:
        """Delete job directories untouched for ``retention_days``; return how many."""
        if not self.directory.exists():
            return 0
        cutoff = time.time() - retention_days * 86400
        removed = 0
        for d in self.directory.iterdir():
            if not d.is_dir() or d.name in keep:
                continue
            try:
                newest = max([d.stat().st_mtime, *(p.stat().st_mtime for p in d.iterdir())])
            except OSError:
                continue
            if newest < cutoff:
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
        return removed
