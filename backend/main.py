"""AE3GIS backend — FastAPI application factory.

Run with ``uvicorn main:create_app --factory``. Tests call ``create_app`` with
their own ``Settings`` and a ``FakeEngine``; nothing happens at import time.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import catalog as node_catalog
from api import (
    captures,
    catalog,
    deployment,
    images,
    jobs,
    presets,
    system,
    topologies,
    traffic,
)
from api.errors import install_error_handlers
from config import API_VERSION, Settings, get_settings
from db.migrations import run_migrations
from db.session import make_engine, make_session_factory
from engine.base import DeploymentEngine
from engine.fake import make_engine as make_deployment_engine
from services import capture, reconcile
from services import traffic as traffic_service
from services.artifacts import ArtifactStore
from services.deployment import register_handlers
from services.images import ImageManager
from services.joblogs import JobLogStore
from services.jobs import JobRunner, recover_stale_jobs
from services.live import LiveHub
from services.sources import Sources

# Job kinds cancelled (rather than awaited) at shutdown.
SHUTDOWN_CANCEL_KINDS: tuple[str, ...] = ("build", "sync_source")
# Open-ended job kinds stopped at shutdown: they keep what they recorded, and a
# restart (or a dev reload) does not wait on a capture that runs for hours.
SHUTDOWN_STOP_KINDS: tuple[str, ...] = ("capture", "traffic")

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, engine: DeploymentEngine | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    settings.ensure_dirs()
    settings.ensure_instance_id()

    run_migrations(settings.database_url)
    session_factory = make_session_factory(make_engine(settings.database_url))
    engine = engine or make_deployment_engine(settings.engine)
    logs = JobLogStore(settings.job_logs_dir, max_bytes=settings.job_log_max_bytes)
    artifacts = ArtifactStore(settings.artifacts_dir)
    runner = JobRunner(session_factory, engine, logs)
    runner.artifacts = artifacts
    runner.settings = settings
    runner.live = LiveHub()
    register_handlers(runner)
    capture.register(runner)
    traffic_service.register(runner)
    image_manager = ImageManager(settings, runner, Sources(settings, node_catalog.sources()))
    image_manager.register()
    runner.images = image_manager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runner.bind_loop(asyncio.get_running_loop())
        ok, detail = await engine.is_available()
        (log.info if ok else log.warning)("Deployment engine '%s': %s", engine.name, detail)
        stale = recover_stale_jobs(session_factory)
        if stale:
            log.warning("Failed %d job(s) left running by a previous process", stale)
        logs.gc(settings.job_log_retention_days)
        artifacts.gc(settings.artifact_retention_days)
        if ok:
            # Capture/traffic jobs of a previous process were just failed; their
            # sidecars (this backend's, by owner label) go too.
            try:
                removed = await engine.remove_sidecars(owner=settings.instance_id)
                if removed:
                    log.warning("Removed %d sidecar(s) left by a previous process", removed)
            except Exception as exc:  # pragma: no cover - environment dependent
                log.warning("Sidecar sweep skipped: %s", exc)
            try:
                with session_factory() as db:
                    summary = await reconcile.apply(db, engine)
                if summary["reset"] or summary["orphans"]:
                    log.warning("Reconcile: %s", summary)
            except Exception as exc:  # pragma: no cover - environment dependent
                log.warning("Startup reconcile skipped: %s", exc)
        yield
        # Long builds are cancelled rather than awaited, so a restart (or a dev
        # reload) does not hang on them; everything else finishes.
        await runner.shutdown(cancel_kinds=SHUTDOWN_CANCEL_KINDS, stop_kinds=SHUTDOWN_STOP_KINDS)

    app = FastAPI(
        title="AE3GIS API",
        version=API_VERSION,
        lifespan=lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.engine = engine
    app.state.runner = runner
    app.state.images = image_manager
    app.state.artifacts = artifacts
    app.state.live = runner.live

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=settings.cors_origin_list != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    for r in (
        topologies.router,
        deployment.router,
        jobs.router,
        captures.router,
        traffic.router,
        images.router,
        system.router,
        catalog.router,
        presets.router,
    ):
        app.include_router(r)
    return app
