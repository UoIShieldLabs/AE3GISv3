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

from api import catalog, deployment, jobs, presets, system, topologies
from api.errors import install_error_handlers
from config import Settings, get_settings
from db.migrations import run_migrations
from db.session import make_engine, make_session_factory
from engine.base import DeploymentEngine
from engine.fake import make_engine as make_deployment_engine
from services import reconcile
from services.deployment import register_handlers
from services.jobs import JobRunner, recover_stale_jobs

API_VERSION = "3.1.0"

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, engine: DeploymentEngine | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    settings.ensure_dirs()

    run_migrations(settings.database_url)
    session_factory = make_session_factory(make_engine(settings.database_url))
    engine = engine or make_deployment_engine(settings.engine)
    runner = JobRunner(session_factory, engine)
    register_handlers(runner)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runner.bind_loop(asyncio.get_running_loop())
        ok, detail = await engine.is_available()
        (log.info if ok else log.warning)("Deployment engine '%s': %s", engine.name, detail)
        stale = recover_stale_jobs(session_factory)
        if stale:
            log.warning("Failed %d job(s) left running by a previous process", stale)
        if ok:
            try:
                with session_factory() as db:
                    summary = await reconcile.apply(db, engine)
                if summary["reset"] or summary["orphans"]:
                    log.warning("Reconcile: %s", summary)
            except Exception as exc:  # pragma: no cover - environment dependent
                log.warning("Startup reconcile skipped: %s", exc)
        yield
        await runner.wait_idle()

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
        system.router,
        catalog.router,
        presets.router,
    ):
        app.include_router(r)
    return app
