"""Deploy / destroy as jobs, plus the runtime view the UI polls."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from api.errors import Conflict, Invalid
from db.models import Job, Topology
from domain import saved_state, validation
from domain.plan import LabPlan
from domain.topology import images_in
from engine.base import DeploymentEngine, EngineState, NodeLog
from services import activity, events, jobs, topologies
from services.jobs import JobRunner

VERIFY_TIMEOUT_S = 15.0
VERIFY_POLL_S = 1.0


# ── starting jobs (called from requests) ─────────────────────────────


def start_deploy(
    db: Session, runner: JobRunner, topo: Topology, *, admit: Callable[[], None] | None = None
) -> Job:
    """``admit`` (e.g. a student's lab cap) runs under the admission lock, after
    the state checks, and raises to refuse the deploy."""
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
        if admit is not None:
            admit()
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


def start_destroy(db: Session, runner: JobRunner, topo: Topology, *, save: bool = False) -> Job:
    """Start a destroy job; ``save`` first commits every node (see ``domain.saved_state``)."""
    with runner.admission:
        db.refresh(topo)
        if jobs.active_job(db, topo.id):
            raise Conflict("A job is already running for this topology", code="job_active")
        if topo.status not in ("deployed", "error") or not topo.engine_state:
            raise Conflict(
                "Nothing is deployed for this topology", code="bad_state", status=topo.status
            )
        if save and topo.status != "deployed":
            raise Conflict(
                "Only a deployed lab can be saved; destroy it without saving",
                code="bad_state",
                status=topo.status,
            )
        topo.status = "destroying"
        job = jobs.create_job(
            db,
            "destroy",
            subject=jobs.topology_subject(topo.id),
            topology_id=topo.id,
            params={"save": save},
        )
        events.record(
            db,
            type="destroy.requested",
            message="Save & destroy requested" if save else "Destroy requested",
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
            # Builds what AE3GIS builds (waiting on builds already running),
            # pulls the rest, and warns about out-of-date images.
            assert runner.images is not None
            await runner.images.prepare_for_deploy(runner, job_id, images_in(data))

        async with runner.step(job_id, "plan"):
            with runner.session_factory() as db:
                topo = db.get(Topology, topology_id)
                plan = topologies.plan_for(topo)
                deployed_version = topo.version
                saved = topo.saved_state
            runner.progress(
                job_id, "plan", f"{len(plan.nodes)} nodes, {len(plan.collision_domains)} links"
            )
            base_images = {n.id: n.image for n in plan.nodes}
            await _restore_saved_state(runner, job_id, saved, plan)

        # Once the engine starts creating containers the job runs to completion
        # (the engine call runs in a worker thread and cannot be interrupted).
        runner.point_of_no_return(job_id)
        async with runner.step(job_id, "deploy"):
            # Record where the lab will be *before* creating it, so a deploy that
            # dies part-way (or a restart) can still find and remove what it made.
            provisional = EngineState(
                engine=engine.name,
                lab_name=plan.name,
                nodes={n.id: n.machine_name for n in plan.nodes},
                links=plan.links(),
                deployed_version=deployed_version,
                base_images=base_images,
            )
            _set_topology(runner, topology_id, engine_state=provisional.to_dict())
            state = await engine.deploy(
                plan, lambda m, jid=job_id: runner.progress(jid, "deploy", m)
            )
            state.links = plan.links()
            state.deployed_version = deployed_version
            state.base_images = base_images
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
                    crashed = await _crashed_nodes(runner, job_id, state)
                    detail = "; ".join(c.summary() for c in crashed)
                    runner.progress(
                        job_id, "verify", detail or f"Not running: {', '.join(not_running)}"
                    )
                    runner.event(
                        job_id,
                        "deploy.partial",
                        f"{len(not_running)} node(s) not running after deploy"
                        + (f" — {detail}" if detail else ""),
                        level="warning",
                        data={
                            "nodes": not_running,
                            "logs": {c.node_id: c.log for c in crashed},
                        },
                    )
                    break
                await asyncio.sleep(VERIFY_POLL_S)
    except (Exception, asyncio.CancelledError) as exc:
        # Leave nothing half-deployed behind; the user sees status=error and can retry.
        with runner.session_factory() as db:
            topo = db.get(Topology, topology_id)
            state = EngineState.from_dict(topo.engine_state) if topo else None
        crashed = []
        if state:
            crashed = await _crashed_nodes(runner, job_id, state)
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
        if crashed and not cancelled:
            detail = "; ".join(c.summary() for c in crashed)
            raise RuntimeError(f"{type(exc).__name__}: {exc} — {detail}") from exc
        raise


async def _restore_saved_state(
    runner: JobRunner, job_id: str, saved: dict[str, Any] | None, plan: LabPlan
) -> None:
    """Inside the plan step: resume nodes from the topology's saved state."""
    refs = saved_state.refs(saved)
    if not refs:
        return
    present = await runner.engine.images_present(refs)
    restore = saved_state.apply(plan, saved, present)
    if restore.applied:
        runner.progress(
            job_id, "plan", f"Resuming {len(restore.applied)} node(s) from the saved state"
        )
        runner.event(
            job_id,
            "deploy.saved_state_restored",
            f"Resumed {len(restore.applied)} node(s) from the state saved "
            f"{(saved or {}).get('created_at', '')}",
            data={"nodes": restore.applied},
        )
    if restore.skipped:
        runner.event(
            job_id,
            "deploy.saved_state_skipped",
            f"{len(restore.skipped)} node(s) start fresh: "
            + "; ".join(f"{n}: {why}" for n, why in restore.skipped.items()),
            level="warning",
            data={"nodes": restore.skipped},
        )


async def _crashed_nodes(runner: JobRunner, job_id: str, state: EngineState) -> list[NodeLog]:
    """Nodes whose container exited, with their output written to the job log."""
    try:
        crashed = await runner.engine.node_logs(state)
    except Exception as exc:  # pragma: no cover - best effort
        runner.log(job_id, f"Could not read node logs: {exc}")
        return []
    for c in crashed:
        runner.log(job_id, f"── {c.summary()}")
        for line in c.log.splitlines():
            runner.log(job_id, f"   {c.name} | {line}")
    return crashed


async def run_destroy(runner: JobRunner, job_id: str) -> None:
    engine = runner.engine
    topology_id, _, raw_state, _ = _load(runner, job_id)
    state = EngineState.from_dict(raw_state)
    with runner.session_factory() as db:
        job = db.get(Job, job_id)
        save = bool((job.params or {}).get("save"))
        topo = db.get(Topology, topology_id)
        previous = topo.saved_state if topo else None
    try:
        async with runner.step(job_id, "stop"):
            # Captures and traffic runs keep what they recorded; their sidecars
            # go before the lab does.
            stopped = await activity.stop_all(runner, topology_id)
            runner.progress(
                job_id,
                "stop",
                f"Stopped {stopped} capture/traffic job(s)" if stopped else "Nothing running",
            )
        if save and state:
            try:
                async with runner.step(job_id, "save"):
                    saved = await _save_state(runner, job_id, topology_id, state)
            except Exception:
                # Nothing was removed: the lab stays up, and so does the old save.
                _set_topology(runner, topology_id, status="deployed")
                raise
            _set_topology(runner, topology_id, saved_state=saved)
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
        # A save replaces the previous one; a plain destroy discards it, so only
        # an explicit save can be resumed. Either way the old images are unused now.
        kept = set(saved_state.refs(saved)) if save and state else set()
        await engine.remove_images([r for r in saved_state.refs(previous) if r not in kept])
        patch: dict[str, Any] = {"status": "idle", "engine_state": None}
        if not kept:
            patch["saved_state"] = None
        _set_topology(runner, topology_id, **patch)
    except Exception:
        with runner.session_factory() as db:
            topo = db.get(Topology, topology_id)
            if topo and topo.status == "destroying":
                topo.status = "error"
                db.commit()
        raise


async def _save_state(
    runner: JobRunner, job_id: str, topology_id: str, state: EngineState
) -> dict[str, Any]:
    """Commit every node; return the new ``Topology.saved_state`` record."""
    now = datetime.now(UTC)
    base_images = dict(state.base_images)
    if not base_images:  # a lab deployed before base images were recorded
        with runner.session_factory() as db:
            plan = topologies.plan_for(db.get(Topology, topology_id))
        base_images = {n.id: n.image for n in plan.nodes}
    refs = await runner.engine.snapshot_nodes(
        state,
        saved_state.repository(topology_id),
        saved_state.tag_suffix(now),
        lambda m, jid=job_id: runner.progress(jid, "save", m),
    )
    runner.progress(job_id, "save", f"Saved {len(refs)} node(s)")
    runner.event(
        job_id,
        "destroy.saved_state",
        f"Saved the state of {len(refs)} node(s)",
        data={"nodes": sorted(refs)},
    )
    return saved_state.make(refs, base_images, deployed_version=state.deployed_version, now=now)


def discard_saved_state_refs(db: Session, topo: Topology) -> list[str]:
    """Clear a topology's saved state; return the images to remove.

    Not while a job runs or a lab is up (its containers may run those images).
    """
    if jobs.active_job(db, topo.id):
        raise Conflict("A job is already running for this topology", code="job_active")
    if topo.status not in ("idle", "error"):
        raise Conflict(
            "Destroy the deployment before discarding its saved state",
            code="bad_state",
            status=topo.status,
        )
    refs = saved_state.refs(topo.saved_state)
    topo.saved_state = None
    events.record(
        db, type="saved_state.discarded", message="Saved state discarded", topology_id=topo.id
    )
    db.commit()
    return refs


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
        "activity": activity.active_for_topology(db, topo.id),
        "nodes": nodes,
        "saved": saved_state.summary(topo.saved_state),
    }


def deployed_links(topo: Topology) -> tuple[list[dict[str, Any]], str]:
    """The deployed lab's links and where they came from.

    ``deployed``: saved at deploy time. ``recomputed``: a lab deployed before
    links were saved, so the plan is rebuilt from the current data (right
    unless the topology was edited since). ``none``: nothing is deployed.
    """
    state = EngineState.from_dict(topo.engine_state)
    if topo.status != "deployed" or not state:
        return [], "none"
    if state.links:
        return state.links, "deployed"
    return topologies.plan_for(topo).links(), "recomputed"
