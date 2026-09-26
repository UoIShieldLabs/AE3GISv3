"""Images AE3GIS builds from Dockerfiles: status, build jobs, and deploy prep.

- *Status* compares each local image with the catalog and its source (see
  ``domain.images``); nothing is scanned at startup.
- *Builds* are jobs (subject ``image:<ref>``), deduplicated per image and
  limited to ``max_concurrent_builds`` at a time. A build snapshots its context
  first, so a sync running meanwhile cannot change what gets built.
- *Syncs* are jobs (subject ``source:<name>``) that refresh a git source and
  report which built images it made stale.
- A deploy's ``images`` step calls ``prepare_for_deploy``: build what is
  missing (joining builds already running), pull registry images, warn about
  stale ones.
"""

from __future__ import annotations

import asyncio
import re
import shutil
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

import catalog
from api.errors import Conflict, Invalid
from catalog.models import BuildSource
from config import Settings
from db.models import Job
from domain.images import (
    LABEL_CREATED,
    LABEL_FINGERPRINT,
    LABEL_REF,
    LABEL_REVISION,
    LABEL_SOURCE,
    SKIPPED_NAMES,
    StatusInput,
    fingerprint,
    image_status,
)
from engine.base import BuildError, BuildSpec, BuildSupport
from services import jobs
from services.jobs import JobRunner
from services.sources import SourceError, Sources, read_context

# BuildKit step headers, e.g. "#8 [4/9] RUN apt-get update" or "#7 [builder 2/5] COPY …".
_STEP_RE = re.compile(r"^#\d+ \[(?:[^\]]*?\s)?(\d+)/(\d+)\] (.+)$")
_STEP_MESSAGE_INTERVAL_S = 1.0
_SUPPORT_TTL_S = 30.0
_RELAY_INTERVAL_S = 1.0


def image_subject(ref: str) -> str:
    return f"image:{ref}"


def source_subject(name: str) -> str:
    return f"source:{name}"


def _short(revision: str | None) -> str:
    return revision[:12] if revision else "—"


class ImageManager:
    def __init__(self, settings: Settings, runner: JobRunner, sources: Sources) -> None:
        self.settings = settings
        self.runner = runner
        self.sources = sources
        self._slots: asyncio.Semaphore | None = None
        self._support: tuple[float, BuildSupport] | None = None

    @property
    def engine(self):
        return self.runner.engine

    def register(self) -> None:
        self.runner.register("build", self.run_build, cancellable=True)
        self.runner.register("sync_source", self.run_sync, cancellable=True)

    @property
    def slots(self) -> asyncio.Semaphore:
        if self._slots is None:
            self._slots = asyncio.Semaphore(max(1, self.settings.max_concurrent_builds))
        return self._slots

    async def support(self, *, refresh: bool = False) -> BuildSupport:
        now = time.monotonic()
        if refresh or self._support is None or now - self._support[0] > _SUPPORT_TTL_S:
            self._support = (now, await self.engine.build_support())
        return self._support[1]

    # ── catalog lookups ──
    @staticmethod
    def build_source(ref: str) -> BuildSource | None:
        spec = catalog.image_spec(ref)
        if spec is not None and isinstance(spec.source, BuildSource):
            return spec.source
        return None

    @staticmethod
    def catalog_refs() -> list[str]:
        return list(catalog.load_model().images)

    def expected_fingerprint(self, ref: str) -> str | None:
        src = self.build_source(ref)
        if src is None:
            return None
        try:
            ctx = self.sources.context_dir(src.repo, src.context)
        except SourceError:
            return None
        return fingerprint(read_context(ctx), src.dockerfile, src.args)

    def unavailable_reason(self, ref: str, support: BuildSupport) -> str | None:
        """Why this host cannot build ``ref`` right now (None: it can)."""
        src = self.build_source(ref)
        spec = catalog.image_spec(ref)
        if src is None or spec is None:
            return "Not an image AE3GIS builds"
        if not support.ok:
            return support.detail
        if spec.platforms and support.platform not in spec.platforms:
            return f"Builds only for {', '.join(spec.platforms)}; this host is {support.platform}"
        reason = self.sources.unavailable_reason(src.repo)
        if reason:
            return reason
        if self.sources.root(src.repo).is_dir():
            try:
                self.sources.context_dir(src.repo, src.context)
            except SourceError as exc:
                return str(exc)
        return None

    # ── status ──
    async def statuses(self, refs: list[str]) -> list[dict[str, Any]]:
        refs = list(dict.fromkeys(r for r in refs if r))
        infos = await self.engine.inspect_images(refs)
        support: BuildSupport | None = None
        rows: list[dict[str, Any]] = []
        with self.runner.session_factory() as db:
            for ref in refs:
                spec = catalog.image_spec(ref)
                src = self.build_source(ref)
                info = infos.get(ref)
                active = jobs.active_for_subject(db, image_subject(ref)) if src else None
                last = jobs.last_for_subject(db, image_subject(ref)) if src else None
                unavailable = None
                if src is not None and info is None:
                    support = support or await self.support()
                    unavailable = self.unavailable_reason(ref, support)
                labels = info.labels if info else {}
                expected = self.expected_fingerprint(ref)
                status, reason = image_status(
                    StatusInput(
                        buildable=src is not None,
                        present=info is not None,
                        built_fingerprint=labels.get(LABEL_FINGERPRINT),
                        expected_fingerprint=expected,
                        unavailable_reason=unavailable,
                        building=active is not None,
                        last_build_error=last.error if last and last.status == "failed" else None,
                    )
                )
                rows.append(
                    {
                        "ref": ref,
                        "display_name": spec.displayName if spec else ref,
                        "description": spec.description if spec else "",
                        "stability": spec.stability if spec else "stable",
                        "kind": "build" if src else "registry",
                        "source": src.repo if src else None,
                        "status": status,
                        "reason": reason,
                        "expected_fingerprint": expected,
                        "built_fingerprint": labels.get(LABEL_FINGERPRINT),
                        "built_revision": labels.get(LABEL_REVISION),
                        "created": info.created if info else None,
                        "size": info.size if info else None,
                        "platforms": spec.platforms if spec else None,
                        "active_job": jobs.job_to_dict(active) if active else None,
                        "last_job": jobs.job_to_dict(last) if last else None,
                    }
                )
        return rows

    def source_rows(self) -> list[dict[str, Any]]:
        rows = []
        with self.runner.session_factory() as db:
            for name in self.sources.specs:
                st = self.sources.state(name)
                active = jobs.active_for_subject(db, source_subject(name))
                last = jobs.last_for_subject(db, source_subject(name))
                rows.append(
                    {
                        "name": name,
                        "kind": st.kind,
                        "url": st.url,
                        "ref": st.ref,
                        "path": str(st.path),
                        "available": st.available,
                        "can_sync": st.can_sync,
                        "revision": st.revision,
                        "detail": st.detail,
                        "active_job": jobs.job_to_dict(active) if active else None,
                        "last_job": jobs.job_to_dict(last) if last else None,
                    }
                )
        return rows

    async def report(self, refs: list[str]) -> dict[str, Any]:
        support = await self.support()
        return {
            "host": {
                "platform": support.platform,
                "can_build": support.ok,
                "detail": support.detail,
            },
            "sources": self.source_rows(),
            "images": await self.statuses(refs),
        }

    # ── starting jobs ──
    def start_builds(self, db: Session, refs: list[str], *, fresh: bool = False) -> list[Job]:
        """One build job per ref; an image already building returns its running job."""
        picked: list[tuple[Job, bool]] = []
        with self.runner.admission:
            for ref in dict.fromkeys(refs):
                if self.build_source(ref) is None:
                    raise Invalid(f"'{ref}' is not an image AE3GIS builds", code="not_buildable")
                existing = jobs.active_for_subject(db, image_subject(ref))
                if existing is not None:
                    picked.append((existing, False))
                    continue
                job = jobs.create_job(
                    db, "build", subject=image_subject(ref), params={"ref": ref, "fresh": fresh}
                )
                picked.append((job, True))
            db.commit()
        for job, new in picked:
            if new:
                self.runner.submit(job.id)
        return [job for job, _ in picked]

    def start_sync(self, db: Session, name: str) -> Job:
        try:
            state = self.sources.state(name)
        except SourceError as exc:
            raise Invalid(str(exc), code="unknown_source") from exc
        if not state.can_sync:
            raise Conflict(f"Source '{name}' can't be synced: {state.detail}", code="not_syncable")
        with self.runner.admission:
            job = jobs.active_for_subject(db, source_subject(name))
            new = job is None
            if new:
                job = jobs.create_job(
                    db, "sync_source", subject=source_subject(name), params={"name": name}
                )
                db.commit()
        if new:
            self.runner.submit(job.id)
        return job

    # ── job handlers ──
    def _params(self, job_id: str) -> dict[str, Any]:
        with self.runner.session_factory() as db:
            job = db.get(Job, job_id)
            return dict(job.params or {}) if job else {}

    async def run_build(self, runner: JobRunner, job_id: str) -> None:
        params = self._params(job_id)
        ref = str(params.get("ref", ""))
        fresh = bool(params.get("fresh"))
        src = self.build_source(ref)
        if src is None:
            raise BuildError(f"'{ref}' is no longer an image AE3GIS builds")

        async with runner.step(job_id, "source"):
            support = await self.support(refresh=True)
            reason = self.unavailable_reason(ref, support)
            if reason:
                raise BuildError(reason)
            await self.sources.ensure(src.repo, lambda m: runner.log(job_id, m))
            revision = self.sources.state(src.repo).revision
            runner.progress(
                job_id, "source", f"{src.repo} @ {_short(revision)} ({support.platform})"
            )

        snapshot = self.settings.build_ctx_dir / job_id
        try:
            async with runner.step(job_id, "snapshot"):
                async with self.sources.lock(src.repo):
                    ctx = self.sources.context_dir(src.repo, src.context)
                    await asyncio.to_thread(
                        shutil.copytree,
                        ctx,
                        snapshot,
                        symlinks=True,
                        ignore=shutil.ignore_patterns(*SKIPPED_NAMES),
                    )
                fp = await asyncio.to_thread(
                    lambda: fingerprint(read_context(snapshot), src.dockerfile, src.args)
                )
                runner.progress(job_id, "snapshot", f"{src.context} · fingerprint {fp[:12]}")

            async with runner.step(job_id, "build", "Waiting for a build slot"):
                async with self.slots:
                    runner.progress(
                        job_id, "build", "Building" + (" without cache (fresh)" if fresh else "")
                    )
                    labels = {
                        LABEL_FINGERPRINT: fp,
                        LABEL_SOURCE: f"{src.repo}/{src.context}",
                        LABEL_REF: ref,
                        LABEL_CREATED: datetime.now(UTC).isoformat(),
                    }
                    if revision:
                        labels[LABEL_REVISION] = revision
                    spec = BuildSpec(
                        ref=ref,
                        context=snapshot,
                        dockerfile=src.dockerfile,
                        args=dict(src.args),
                        labels=labels,
                        pull=fresh,
                        no_cache=fresh,
                    )
                    await self.engine.build_image(spec, self._on_build_line(runner, job_id))

            async with runner.step(job_id, "verify"):
                info = (await self.engine.inspect_images([ref])).get(ref)
                if info is None:
                    raise BuildError(f"The build finished but {ref} is not in the image store")
                if info.labels.get(LABEL_FINGERPRINT) != fp:
                    raise BuildError(f"{ref} does not carry the expected fingerprint label")
                size = f" · {info.size / 1e6:.0f} MB" if info.size else ""
                runner.progress(job_id, "verify", f"{ref}{size}")
        finally:
            await asyncio.to_thread(shutil.rmtree, snapshot, True)

    @staticmethod
    def _on_build_line(runner: JobRunner, job_id: str):
        last = 0.0

        def on_line(line: str) -> None:
            nonlocal last
            runner.log(job_id, line)
            m = _STEP_RE.match(line)
            if not m:
                return
            now = time.monotonic()
            if now - last >= _STEP_MESSAGE_INTERVAL_S:
                last = now
                text = m.group(3)
                text = text if len(text) <= 120 else text[:119] + "…"
                runner.patch_step(job_id, "build", message=f"[{m.group(1)}/{m.group(2)}] {text}")

        return on_line

    async def run_sync(self, runner: JobRunner, job_id: str) -> None:
        name = str(self._params(job_id).get("name", ""))
        async with runner.step(job_id, "fetch"):
            before = self.sources.state(name).revision
            after = await self.sources.sync(name, lambda m: runner.log(job_id, m))
            runner.progress(
                job_id,
                "fetch",
                "Already up to date" if before == after else f"{_short(before)} → {_short(after)}",
            )
        async with runner.step(job_id, "compare"):
            refs = [
                ref
                for ref in self.catalog_refs()
                if (src := self.build_source(ref)) is not None and src.repo == name
            ]
            rows = await self.statuses(refs)
            built = [r for r in rows if r["status"] in ("ready", "stale", "unmanaged")]
            stale = [r["display_name"] for r in rows if r["status"] == "stale"]
            if stale:
                summary = f"{len(stale)} built image(s) have updates: {', '.join(stale)}"
            elif built:
                summary = f"All {len(built)} built image(s) are up to date"
            else:
                summary = "None of its images are built yet"
            runner.progress(job_id, "compare", summary)

    # ── deploy (and any job that runs images) ──
    async def prepare_for_deploy(self, runner: JobRunner, job_id: str, refs: list[str]) -> None:
        """Run inside a deploy's ``images`` step: make every image available."""
        await self.ensure_images(runner, job_id, refs)

    async def ensure_images(
        self,
        runner: JobRunner,
        job_id: str,
        refs: list[str],
        *,
        step: str = "images",
        stale_event: str = "deploy.images_stale",
    ) -> None:
        """Inside a job's ``step``: build (or join the running build of) what
        AE3GIS builds, pull the rest, and warn about out-of-date images."""
        rows = await self.statuses(refs)
        unavailable = [r for r in rows if r["status"] == "unavailable"]
        if unavailable:
            raise RuntimeError(
                "Can't build "
                + "; ".join(f"{r['display_name']} ({r['ref']}): {r['reason']}" for r in unavailable)
            )
        to_build = [
            r["ref"]
            for r in rows
            if r["kind"] == "build" and r["status"] in ("missing", "failed", "building")
        ]
        to_pull = [r["ref"] for r in rows if r["kind"] == "registry" and r["status"] == "missing"]
        stale = [r for r in rows if r["status"] == "stale"]
        names = {r["ref"]: r["display_name"] for r in rows}

        builds: list[Job] = []
        if to_build:
            with runner.session_factory() as db:
                builds = self.start_builds(db, to_build)
            runner.patch_step(job_id, step, jobs=[j.id for j in builds])
            runner.log(job_id, "Building " + ", ".join(names[r] for r in to_build))

        for i, image in enumerate(to_pull, 1):
            runner.progress(job_id, step, f"Pulling {image} ({i}/{len(to_pull)})")
            await self.engine.pull_image(image, lambda m, jid=job_id: runner.progress(jid, step, m))

        for i, build in enumerate(builds, 1):
            ref = str((build.params or {}).get("ref", ""))
            label = f"Building {names.get(ref, ref)} ({i}/{len(builds)})"
            runner.progress(job_id, step, label)
            final = await self._wait_relaying(runner, job_id, build.id, label, step)
            if final is None or final.status != "succeeded":
                status = final.status if final else "vanished"
                error = f": {final.error}" if final and final.error else ""
                raise RuntimeError(f"Building {names.get(ref, ref)} {status}{error}")

        if stale:
            listed = ", ".join(r["display_name"] for r in stale)
            runner.event(
                job_id,
                stale_event,
                f"Using {len(stale)} out-of-date image(s): {listed}. Rebuild them to pick up "
                "their source changes.",
                level="warning",
                data={"refs": [r["ref"] for r in stale]},
            )
        parts = []
        if builds:
            parts.append(f"{len(builds)} built")
        if to_pull:
            parts.append(f"{len(to_pull)} pulled")
        if stale:
            parts.append(f"{len(stale)} out of date")
        runner.progress(
            job_id,
            step,
            f"{len(rows)} image(s) ready" + (f" ({', '.join(parts)})" if parts else ""),
        )

    async def _wait_relaying(
        self, runner: JobRunner, job_id: str, build_id: str, label: str, step: str = "images"
    ) -> Job | None:
        """Wait for a build, mirroring its current step into the deploy's step message."""
        waiter = asyncio.ensure_future(runner.wait(build_id))
        try:
            while True:
                done, _ = await asyncio.wait({waiter}, timeout=_RELAY_INTERVAL_S)
                if done:
                    return waiter.result()
                with runner.session_factory() as db:
                    job = db.get(Job, build_id)
                    running = next(
                        (s for s in (job.steps if job else []) or [] if s["status"] == "running"),
                        None,
                    )
                if running and running.get("message"):
                    runner.patch_step(job_id, step, message=f"{label} · {running['message']}")
        finally:
            if not waiter.done():
                waiter.cancel()
