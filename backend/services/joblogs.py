"""Append-only log files for jobs (``<logs_dir>/<job_id>.log``).

Build output can run to tens of thousands of lines, so logs live on disk rather
than in SQLite, where every line would contend for the single write lock.
Readers page through a log by byte offset. A log is capped at ``max_bytes``;
past the cap the most recent lines are kept in memory and appended when the job
closes its log, because the useful part of a failed build is the end.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

TAIL_LINES_KEPT = 300


@dataclass
class _Open:
    fh: BinaryIO
    size: int
    dropped: int = 0
    tail: deque[str] = field(default_factory=lambda: deque(maxlen=TAIL_LINES_KEPT))


@dataclass
class LogChunk:
    offset: int
    next_offset: int
    size: int
    text: str


class JobLogStore:
    def __init__(self, directory: Path, max_bytes: int = 8_000_000) -> None:
        self.directory = directory
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        self._open: dict[str, _Open] = {}

    def path(self, job_id: str) -> Path:
        # Job ids are server-generated hex; never let one address another file.
        if not job_id.isalnum():
            raise ValueError(f"Invalid job id: {job_id!r}")
        return self.directory / f"{job_id}.log"

    def append(self, job_id: str, line: str) -> None:
        """Append one line (safe from any thread)."""
        data = (line.rstrip("\n") + "\n").encode("utf-8", errors="replace")
        with self._lock:
            state = self._open.get(job_id)
            if state is None:
                self.directory.mkdir(parents=True, exist_ok=True)
                fh = self.path(job_id).open("ab")
                state = self._open[job_id] = _Open(fh=fh, size=fh.tell())
            if state.size + len(data) > self.max_bytes:
                if len(state.tail) == state.tail.maxlen:
                    state.dropped += len(state.tail[0].encode("utf-8", errors="replace"))
                state.tail.append(data.decode("utf-8"))
                return
            state.fh.write(data)
            state.fh.flush()  # readers poll the file while the job runs
            state.size += len(data)

    def close(self, job_id: str) -> None:
        """Flush a capped log's kept tail. Call when the job finishes."""
        with self._lock:
            state = self._open.pop(job_id, None)
            if state is None:
                return
            with state.fh as fh:
                if state.tail:
                    note = f"… log truncated at {self.max_bytes} bytes"
                    if state.dropped:
                        note += f", {state.dropped} more bytes omitted"
                    fh.write(f"{note}; last {len(state.tail)} lines follow …\n".encode())
                    fh.write("".join(state.tail).encode("utf-8", errors="replace"))

    def read(self, job_id: str, offset: int | None = None, limit: int = 65536) -> LogChunk:
        """Read up to ``limit`` bytes from ``offset``, ending on a line boundary.

        With no offset, return the tail of the log (starting on a line boundary).
        """
        p = self.path(job_id)
        size = p.stat().st_size if p.exists() else 0
        limit = max(1024, limit)
        if offset is None:
            start = max(0, size - limit)
        else:
            start = min(max(0, offset), size)
        if start >= size:
            return LogChunk(offset=start, next_offset=start, size=size, text="")
        with p.open("rb") as fh:
            fh.seek(start)
            raw = fh.read(min(limit, size - start))
        if offset is None and start > 0:
            # Tail read: drop the partial first line.
            nl = raw.find(b"\n")
            if 0 <= nl < len(raw) - 1:
                start += nl + 1
                raw = raw[nl + 1 :]
        end = raw.rfind(b"\n")
        if 0 <= end < len(raw) - 1:
            raw = raw[: end + 1]
        return LogChunk(
            offset=start,
            next_offset=start + len(raw),
            size=size,
            text=raw.decode("utf-8", errors="replace"),
        )

    def gc(self, retention_days: float) -> int:
        """Delete logs older than ``retention_days``; return how many."""
        if not self.directory.exists():
            return 0
        cutoff = time.time() - retention_days * 86400
        removed = 0
        for p in self.directory.glob("*.log"):
            if p.stem in self._open:
                continue
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink()
                    removed += 1
            except OSError:
                continue
        return removed
