"""Docker Hub registries whose standard images join the node catalog.

A registry is a Docker Hub namespace the user added (persisted per instance in
the ``registries`` table). A *sync* job (subject ``registry:<id>``) lists the
namespace, keeps the repos whose description carries the ``[ae3gis]`` marker,
reads their images' labels and stores what it saw as the registry's
*snapshot*. The catalog in effect is the built-in one merged with every
snapshot (``catalog.registry.merge``), recomputed at startup and after each
add, remove or sync: no network involved, so a registry that has gone away
keeps serving what it last loaded.

Label reads cost Docker Hub pulls; a sync reuses the labels of every image
whose digest has not changed, and stops reading while only
``registry_pull_reserve`` pulls are left (the rest wait for the next sync).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

import catalog
from api.errors import Conflict, Invalid, NotFound
from catalog.registry import Report, Snapshot, merge
from config import Settings
from db.models import Job, Registry
from domain.image_labels import MARKER, is_candidate
from services import jobs
from services.dockerhub import DockerHubClient, HubError, RateLimited, hub_url, parse_hub_url
from services.jobs import JobRunner

log = logging.getLogger(__name__)


def registry_subject(registry_id: str) -> str:
    return f"registry:{registry_id}"


class RegistryManager:
    def __init__(
        self,
        settings: Settings,
        runner: JobRunner,
        hub: Callable[[], DockerHubClient] | None = None,
    ) -> None:
        self.settings = settings
        self.runner = runner
        # A fresh client per sync; tests swap in one over a mock transport.
        self.hub = hub or (lambda: DockerHubClient(timeout=settings.registry_timeout_s))
        self.reports: dict[str, Report] = {}

    def register(self) -> None:
        self.runner.register("sync_registry", self.run_sync, cancellable=True)

    # ── the catalog ──
    def apply_overlay(self) -> None:
        """Merge every registry's snapshot over the built-in catalog and serve it."""
        with self.runner.session_factory() as db:
            rows = db.query(Registry).order_by(Registry.created_at, Registry.id).all()
            snapshots = [Snapshot.from_dict(r.namespace, r.snapshot) for r in rows]
        try:
            merged, self.reports = merge(catalog.builtin_model(), snapshots)
        except Exception:  # a bad snapshot must never take the catalog down
            log.exception("Could not merge registry images; serving the built-in catalog")
            catalog.set_registry_overlay(None)
            self.reports = {}
            return
        catalog.set_registry_overlay(merged if rows else None)

    # ── rows ──
    def rows(self) -> list[dict[str, Any]]:
        with self.runner.session_factory() as db:
            regs = db.query(Registry).order_by(Registry.created_at, Registry.id).all()
            return [self._row(db, r) for r in regs]

    def row(self, db: Session, registry_id: str) -> dict[str, Any]:
        return self._row(db, self._get(db, registry_id))

    def _row(self, db: Session, reg: Registry) -> dict[str, Any]:
        snap = reg.snapshot or {}
        report = self.reports.get(reg.namespace) or Report()
        active = jobs.active_for_subject(db, registry_subject(reg.id))
        last = jobs.last_for_subject(db, registry_subject(reg.id))
        return {
            "id": reg.id,
            "namespace": reg.namespace,
            "url": reg.url,
            "hub_url": hub_url(reg.namespace),
            "created_at": reg.created_at,
            "synced_at": reg.synced_at,
            "repositories": int(snap.get("repositories") or 0),
            "skipped": int(snap.get("skipped") or 0),
            "pending": list(snap.get("pending") or []),
            "pulls_remaining": snap.get("pulls_remaining"),
            "loaded": report.loaded,
            "rejected": report.rejected,
            "warnings": report.warnings,
            "active_job": jobs.job_to_dict(active) if active else None,
            "last_job": jobs.job_to_dict(last) if last else None,
        }

    @staticmethod
    def _get(db: Session, registry_id: str) -> Registry:
        reg = db.get(Registry, registry_id)
        if reg is None:
            raise NotFound("Registry")
        return reg

    # ── changes ──
    def add(self, db: Session, url: str) -> Registry:
        try:
            namespace = parse_hub_url(url)
        except ValueError as exc:
            raise Invalid(str(exc), code="invalid_registry") from exc
        if db.query(Registry).filter(Registry.namespace == namespace).first():
            raise Conflict(
                f"Docker Hub namespace {namespace!r} is already added", "registry_exists"
            )
        reg = Registry(namespace=namespace, url=url.strip())
        db.add(reg)
        db.commit()
        self.start_sync(db, reg.id)
        return reg

    def remove(self, db: Session, registry_id: str) -> None:
        reg = self._get(db, registry_id)
        if jobs.active_for_subject(db, registry_subject(reg.id)):
            raise Conflict(f"{reg.namespace} is syncing; wait for it to finish", "registry_busy")
        db.delete(reg)
        db.commit()
        self.apply_overlay()

    def start_sync(self, db: Session, registry_id: str) -> Job:
        reg = self._get(db, registry_id)
        subject = registry_subject(reg.id)
        with self.runner.admission:
            job = jobs.active_for_subject(db, subject)
            new = job is None
            if new:
                job = jobs.create_job(
                    db, "sync_registry", subject=subject, params={"registry_id": reg.id}
                )
                db.commit()
        if new:
            self.runner.submit(job.id)
        return job

    # ── the sync job ──
    async def run_sync(self, runner: JobRunner, job_id: str) -> None:
        with runner.session_factory() as db:
            job = db.get(Job, job_id)
            registry_id = str((job.params or {}).get("registry_id", "")) if job else ""
            reg = db.get(Registry, registry_id)
            if reg is None:
                raise RuntimeError("The registry was removed")
            namespace = reg.namespace
            previous = {c["repo"]: c for c in (reg.snapshot or {}).get("candidates", [])}

        host = (await runner.images.support()).platform if runner.images else ""
        prefer = [p for p in (host, "linux/amd64") if p and "unknown" not in p]
        reserve = self.settings.registry_pull_reserve

        async with self.hub() as hub:
            async with runner.step(job_id, "list"):
                repos = await hub.repositories(namespace)
                marked = [r for r in repos if not r.private and is_candidate(r.description)]
                candidates: list[dict[str, Any]] = []
                for repo in marked:
                    tag = await hub.pick_tag(namespace, repo.name)
                    if tag is None:
                        candidates.append(
                            {"repo": repo.name, "tag": "latest", "error": "the repo has no tags"}
                        )
                        continue
                    candidates.append(
                        {
                            "repo": repo.name,
                            "tag": tag.name,
                            "digest": tag.digest,
                            "platforms": tag.platforms,
                        }
                    )
                skipped = len(repos) - len(marked)
                runner.progress(
                    job_id,
                    "list",
                    f"{len(repos)} repositories: {len(marked)} marked {MARKER}, {skipped} skipped",
                )

            async with runner.step(job_id, "inspect"):
                pending: list[str] = []
                reused = read = 0
                remaining: int | None = None
                to_read = []
                for cand in candidates:
                    if cand.get("error"):
                        continue
                    prev = previous.get(cand["repo"])
                    if (
                        prev
                        and prev.get("labels") is not None
                        and prev.get("digest") == cand["digest"]
                        and prev.get("tag") == cand["tag"]
                        and cand["digest"]
                    ):
                        cand["labels"] = prev["labels"]
                        reused += 1
                    else:
                        to_read.append(cand)
                if to_read:
                    first = to_read[0]
                    try:
                        remaining = await hub.remaining(
                            namespace, first["repo"], first["digest"] or first["tag"]
                        )
                    except HubError:
                        remaining = None
                for i, cand in enumerate(to_read, 1):
                    if remaining is not None and remaining <= reserve:
                        pending.append(cand["repo"])
                        continue
                    runner.progress(
                        job_id, "inspect", f"Reading {cand['repo']} ({i}/{len(to_read)})"
                    )
                    try:
                        got = await hub.labels(
                            namespace, cand["repo"], cand["digest"] or cand["tag"], prefer
                        )
                    except RateLimited:
                        remaining = 0
                        pending.append(cand["repo"])
                        continue
                    except HubError as exc:
                        cand["error"] = f"could not read its labels: {exc}"
                        continue
                    cand["labels"] = got.labels
                    read += 1
                    if got.remaining is not None:
                        remaining = got.remaining
                # An image not read this time keeps what the previous sync saw.
                for cand in candidates:
                    if cand["repo"] in pending:
                        prev = previous.get(cand["repo"])
                        if prev and prev.get("labels") is not None:
                            cand.clear()
                            cand.update(prev)
                        else:
                            cand["pending"] = True
                parts = [f"{read} read", f"{reused} unchanged"]
                if pending:
                    parts.append(f"{len(pending)} left for the next sync (Docker Hub pull limit)")
                if remaining is not None:
                    parts.append(f"{remaining} pulls left this hour")
                runner.progress(job_id, "inspect", ", ".join(parts))

        async with runner.step(job_id, "apply"):
            with runner.session_factory() as db:
                reg = db.get(Registry, registry_id)
                if reg is None:
                    raise RuntimeError("The registry was removed")
                reg.snapshot = {
                    "repositories": len(repos),
                    "skipped": skipped,
                    "pending": pending,
                    "pulls_remaining": remaining,
                    "candidates": candidates,
                }
                reg.synced_at = datetime.now(UTC)
                db.commit()
            self.apply_overlay()
            report = self.reports.get(namespace) or Report()
            summary = {
                "loaded": len(report.loaded),
                "rejected": len(report.rejected),
                "skipped": skipped,
                "pending": len(pending),
                "warnings": len(report.warnings),
            }
            runner.set_result(job_id, summary)
            for r in report.rejected:
                runner.log(job_id, f"Rejected {r['repo']}:{r['tag']}: {'; '.join(r['reasons'])}")
            for w in report.warnings:
                runner.log(job_id, f"Warning: {w}")
            text = f"{summary['loaded']} image(s) loaded"
            if summary["rejected"]:
                text += f", {summary['rejected']} rejected"
            if summary["pending"]:
                text += f", {summary['pending']} pending"
            runner.progress(job_id, "apply", text)
