"""Deploy / destroy as jobs, plus the runtime view the UI polls."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from api.errors import Conflict, Invalid
from db.models import Job, Topology
from domain import validation
from domain.topology import images_in
from engine.base import DeploymentEngine, EngineState
from services import events, jobs, topologies
from services.jobs import JobRunner

VERIFY_TIMEOUT_S = 15.0
VERIFY_POLL_S = 1.0


# ── starting jobs (called from requests) ─────────────────────────────


def start_deploy(db: Session, runner: JobRunner, topo: Topology) -> Job:
    with runner.admission:
        db.refresh(topo)
        if jobs.active_job(db, topo.id):
            raise Conflict("A job is already running for this topology", code="job_active")
        if topo.status not in ("idle", "error"):
            raise Conflict(
                f"Cannot deploy while status is '{topo.status}'",
                code="bad_state",
                status=topo.status,
            )
        diags = validation.validate(topo.data)
        if validation.has_errors(diags):
            raise Invalid(
                "The topology has errors that must be fixed before deploying",
                code="validation_failed",
                diagnostics=[d.to_dict() for d in diags],
            )
        topo.status = "deploying"
        job = jobs.create_job(
            db, "deploy", subject=jobs.topology_subject(topo.id), topology_id=topo.id
        )
        events.record(
            db,
            type="deploy.requested",
            message="Deploy requested",
            topology_id=topo.id,
            job_id=job.id,
        )
        db.commit()
    db.refresh(job)
    runner.submit(job.id)
    return job


def start_destroy(db: Session, runner: JobRunner, topo: Topology) -> Job:
    with runner.admission:
        db.refresh(topo)
        if jobs.active_job(db, topo.id):
            raise Conflict("A job is already running for this topology", code="job_active")
        if topo.status not in ("deployed", "error") or not topo.engine_state:
            raise Conflict(
                "Nothing is deployed for this topology", code="bad_state", status=topo.status
            )
        topo.status = "destroying"
        job = jobs.create_job(
            db, "destroy", subject=jobs.topology_subject(topo.id), topology_id=topo.id
        )
        events.record(
            db,
            type="destroy.requested",
            message="Destroy requested",
            topology_id=topo.id,
            job_id=job.id,
        )
        db.commit()
    db.refresh(job)
    runner.submit(job.id)
    return job


# ── job handlers (run by the JobRunner) ──────────────────────────────


def _load(runner: JobRunner, job_id: str) -> tuple[str, dict[str, Any], dict | None, str]:
    with runner.session_factory() as db:
        job = db.get(Job, job_id)
        topo = db.get(Topology, job.topology_id)
        return topo.id, topologies.data_with_name(topo), topo.engine_state, topo.name


def _set_topology(runner: JobRunner, topology_id: str, **patch: Any) -> None:
    with runner.session_factory() as db:
        topo = db.get(Topology, topology_id)
        if topo:
            for k, v in patch.items():
                setattr(topo, k, v)
            db.commit()


async def run_deploy(runner: JobRunner, job_id: str) -> None:
    engine = runner.engine
    topology_id, data, _, _ = _load(runner, job_id)
    try:
        async with runner.step(job_id, "validate"):
            diags = validation.validate(data)
            summary = validation.summarize(diags)
            if summary["warnings"]:
                runner.progress(job_id, "validate", f"{summary['warnings']} warning(s)")
            if validation.has_errors(diags):
                raise RuntimeError(f"{summary['errors']} validation error(s)")

        async with runner.step(job_id, "images"):
            images = images_in(data)
            present = await engine.images_present(images)
            missing = [i for i in images if not present.get(i)]
            if not missing:
                runner.progress(job_id, "images", f"{len(images)} image(s) present")
            for i, image in enumerate(missing, 1):
                runner.progress(job_id, "images", f"Pulling {image} ({i}/{len(missing)})")
                await engine.pull_image(
                    image, lambda m, jid=job_id: runner.progress(jid, "images", m)
                )

        async with runner.step(job_id, "plan"):
            with runner.session_factory() as db:
                topo = db.get(Topology, topology_id)
                plan = topologies.plan_for(topo)
            runner.progress(
                job_id, "plan", f"{len(plan.nodes)} nodes, {len(plan.collision_domains)} links"
            )

        # Once the engine starts creating containers the job runs to completion
        # (the engine call runs in a worker thread and cannot be interrupted).
        runner.point_of_no_return(job_id)
        async with runner.step(job_id, "deploy"):
            state = await engine.deploy(
                plan, lambda m, jid=job_id: runner.progress(jid, "deploy", m)
            )
            _set_topology(runner, topology_id, engine_state=state.to_dict(), status="deployed")

        async with runner.step(job_id, "verify"):
            deadline = asyncio.get_running_loop().time() + VERIFY_TIMEOUT_S
            while True:
                statuses = await engine.status(state)
                not_running = [s.name for s in statuses if s.state != "running"]
                if not not_running:
                    runner.progress(job_id, "verify", f"All {len(statuses)} nodes running")
                    break
                if asyncio.get_running_loop().time() > deadline:
                    runner.progress(job_id, "verify", f"Not running: {', '.join(not_running)}")
                    runner.event(
                        job_id,
                        "deploy.partial",
                        f"{len(not_running)} node(s) not running after deploy",
                        level="warning",
                        data={"nodes": not_running},
                    )
                    break
                await asyncio.sleep(VERIFY_POLL_S)
    except (Exception, asyncio.CancelledError) as exc:
        # Leave nothing half-deployed behind; the user sees status=error and can retry.
        with runner.session_factory() as db:
            topo = db.get(Topology, topology_id)
            state = EngineState.from_dict(topo.engine_state) if topo else None
        if state:
            try:
                await engine.destroy(state)
            except Exception as cleanup_exc:  # pragma: no cover - best effort
                runner.event(
                    job_id,
                    "deploy.cleanup_failed",
                    f"Cleanup failed: {cleanup_exc}",
                    level="error",
                )
        cancelled = isinstance(exc, asyncio.CancelledError)
        # A cancel can only land before the engine created anything: back to idle.
        _set_topology(
            runner, topology_id, status="idle" if cancelled else "error", engine_state=None
        )
        raise


async def run_destroy(runner: JobRunner, job_id: str) -> None:
    engine = runner.engine
    topology_id, _, raw_state, _ = _load(runner, job_id)
    state = EngineState.from_dict(raw_state)
    try:
        async with runner.step(job_id, "undeploy"):
            if state:
                await engine.destroy(state)
            else:
                runner.progress(job_id, "undeploy", "No engine state; nothing to remove")
        async with runner.step(job_id, "verify"):
            if state:
                left = [s.name for s in await engine.status(state) if s.state == "running"]
                if left:
                    raise RuntimeError(f"Still running: {', '.join(left)}")
        _set_topology(runner, topology_id, status="idle", engine_state=None)
    except Exception:
        _set_topology(runner, topology_id, status="error")
        raise


def register_handlers(runner: JobRunner) -> None:
    # Deploys can be cancelled until the engine starts creating containers.
    runner.register("deploy", run_deploy, cancellable=True)
    runner.register("destroy", run_destroy)


# ── runtime view ─────────────────────────────────────────────────────


async def runtime_view(db: Session, engine: DeploymentEngine, topo: Topology) -> dict[str, Any]:
    job = jobs.active_job(db, topo.id)
    nodes: list[dict[str, Any]] = []
    state = EngineState.from_dict(topo.engine_state)
    if state and topo.status in ("deployed", "destroying", "error"):
        try:
            nodes = [
                {"id": s.node_id, "name": s.name, "state": s.state}
                for s in await engine.status(state)
            ]
        except Exception:  # engine unreachable: report nothing rather than fail the poll
            nodes = []
    return {
        "topology_id": topo.id,
        "status": topo.status,
        "version": topo.version,
        "active_job": jobs.job_to_dict(job) if job else None,
        "nodes": nodes,
    }
