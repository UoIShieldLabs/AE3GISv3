"""Where Dockerfiles come from: catalog ``sources`` resolved to directories.

A ``git`` source is cloned into ``<data_dir>/sources/<name>`` on first use and
refreshed by an explicit sync (a job). A ``path`` source, or an override from
``AE3GIS_SOURCE_OVERRIDES``, is used as-is. Only git needs the ``git`` binary;
without it, git sources are unavailable but already-built images still deploy.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import stat
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from catalog.models import GitSource, PathSource, SourceSpec
from config import BASE_DIR, Settings
from domain.images import SKIPPED_NAMES, ContextFile
from engine.base import Progress

GIT_TIMEOUT_S = 300.0


class SourceError(RuntimeError):
    """A source cannot be used (not configured, not synced, git missing…)."""


@dataclass
class SourceState:
    name: str
    kind: str
    url: str | None
    ref: str | None
    path: Path
    available: bool  # the directory exists and can be read
    can_sync: bool
    revision: str | None
    detail: str


def git_available() -> bool:
    return shutil.which("git") is not None


class Sources:
    def __init__(self, settings: Settings, specs: dict[str, SourceSpec]) -> None:
        self.settings = settings
        self.specs = specs
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def lock(self, name: str) -> asyncio.Lock:
        """Held while a source's files change (sync) or are copied (build snapshot)."""
        return self._locks[name]

    def spec(self, name: str) -> SourceSpec:
        try:
            return self.specs[name]
        except KeyError:
            raise SourceError(f"Unknown image source '{name}'") from None

    def is_managed_git(self, name: str) -> bool:
        return isinstance(self.spec(name), GitSource) and name not in self.settings.source_overrides

    def root(self, name: str) -> Path:
        spec = self.spec(name)
        override = self.settings.source_overrides.get(name)
        if override is not None:
            return Path(override)
        if isinstance(spec, PathSource):
            # Relative paths are relative to the backend (e.g. "tools"), not
            # to wherever the process was started.
            path = Path(spec.path)
            return path if path.is_absolute() else BASE_DIR / path
        return self.settings.sources_dir / name

    def state(self, name: str) -> SourceState:
        spec = self.spec(name)
        root = self.root(name)
        managed = self.is_managed_git(name)
        exists = root.is_dir()
        revision = _revision(root) if exists else None
        if managed and not git_available():
            detail = "git is not installed on the backend host"
        elif not exists:
            detail = "Not synced yet (cloned on first build)" if managed else "Directory not found"
        elif name in self.settings.source_overrides:
            detail = "Local override"
        else:
            detail = "Synced" if managed else "Local directory"
        return SourceState(
            name=name,
            kind=spec.kind,
            url=spec.url if isinstance(spec, GitSource) else None,
            ref=spec.ref if isinstance(spec, GitSource) else None,
            path=root,
            available=exists,
            can_sync=managed and git_available(),
            revision=revision,
            detail=detail,
        )

    def unavailable_reason(self, name: str) -> str | None:
        """Why images from this source cannot be built right now (None: they can)."""
        try:
            st = self.state(name)
        except SourceError as exc:
            return str(exc)
        if st.available:
            return None
        if st.can_sync:
            return None  # the first build clones it
        return f"Source '{name}': {st.detail}"

    def context_dir(self, name: str, context: str) -> Path:
        root = self.root(name).resolve()
        ctx = (root / context).resolve()
        if ctx != root and root not in ctx.parents:
            raise SourceError(f"Build context '{context}' escapes source '{name}'")
        if not ctx.is_dir():
            raise SourceError(f"Build context '{context}' not found in source '{name}'")
        return ctx

    async def ensure(self, name: str, log: Progress) -> Path:
        """The source's directory, cloning a git source that was never synced."""
        root = self.root(name)
        if root.is_dir():
            return root
        if not self.is_managed_git(name):
            raise SourceError(f"Source '{name}' directory not found: {root}")
        async with self.lock(name):
            if not root.is_dir():
                await self._clone(name, log)
        return root

    async def sync(self, name: str, log: Progress) -> str | None:
        """Fetch the configured ref and reset to it. Returns the new revision."""
        if not self.is_managed_git(name):
            raise SourceError(f"Source '{name}' is not a git source AE3GIS manages")
        spec = self.spec(name)
        assert isinstance(spec, GitSource)
        root = self.root(name)
        async with self.lock(name):
            if not root.is_dir():
                await self._clone(name, log)
            else:
                await _git(["remote", "set-url", "origin", spec.url], root, log)
                await _git(["fetch", "--depth", "1", "origin", spec.ref], root, log)
                await _git(["reset", "--hard", "FETCH_HEAD"], root, log)
                await _git(["clean", "-ffdx"], root, log)
        return _revision(root)

    async def _clone(self, name: str, log: Progress) -> None:
        if not git_available():
            raise SourceError("git is not installed on the backend host")
        spec = self.spec(name)
        assert isinstance(spec, GitSource)
        root = self.root(name)
        tmp = root.with_name(f".{root.name}.cloning")
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        log(f"Cloning {spec.url} ({spec.ref})")
        try:
            # init + fetch (rather than clone --branch) also accepts a commit id.
            await _git(["init", "-q"], tmp, log)
            await _git(["remote", "add", "origin", spec.url], tmp, log)
            await _git(["fetch", "--depth", "1", "origin", spec.ref], tmp, log)
            await _git(
                ["-c", "advice.detachedHead=false", "checkout", "-q", "FETCH_HEAD"], tmp, log
            )
            tmp.rename(root)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def read_context(ctx: Path) -> list[ContextFile]:
    """Every file under a build context, for fingerprinting (symlinks not followed)."""
    files: list[ContextFile] = []
    for dirpath, dirnames, filenames in os.walk(ctx):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIPPED_NAMES)
        for fname in sorted(filenames):
            if fname in SKIPPED_NAMES:
                continue
            full = Path(dirpath) / fname
            rel = full.relative_to(ctx).as_posix()
            st = full.lstat()
            if stat.S_ISLNK(st.st_mode):
                data = b"symlink:" + os.readlink(full).encode()
            else:
                data = full.read_bytes()
            files.append(ContextFile(rel, bool(st.st_mode & 0o111), data))
    return files


def _revision(root: Path) -> str | None:
    head = root / ".git" / "HEAD"
    if not head.is_file():
        return None
    try:
        ref = head.read_text().strip()
        if ref.startswith("ref: "):
            target = root / ".git" / ref[5:]
            if target.is_file():
                return target.read_text().strip()
            packed = root / ".git" / "packed-refs"
            if packed.is_file():
                for line in packed.read_text().splitlines():
                    parts = line.split()
                    if len(parts) == 2 and parts[1] == ref[5:]:
                        return parts[0]
            return None
        return ref  # detached HEAD: the commit id itself
    except OSError:
        return None


async def _git(args: list[str], cwd: Path, log: Progress) -> str:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), GIT_TIMEOUT_S)
    except (TimeoutError, asyncio.CancelledError):
        proc.kill()
        await proc.wait()
        raise
    text = out.decode("utf-8", errors="replace").strip()
    for line in text.splitlines():
        log(f"git {args[0]}: {line}")
    if proc.returncode != 0:
        raise SourceError(
            f"git {' '.join(args)} failed: {text.splitlines()[-1] if text else proc.returncode}"
        )
    return text
