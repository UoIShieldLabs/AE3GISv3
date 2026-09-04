"""AE3GIS backend — FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401 - register ORM metadata before create_all
from config import CORS_ORIGINS
from database import Base
from database import engine as db_engine
from engine.kathara.engine import engine as deployment_engine
from routers import catalog, deployment, presets, topologies

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=db_engine)
    ok, detail = await deployment_engine.is_available()
    if ok:
        log.info("Deployment engine '%s' ready: %s", deployment_engine.name, detail)
    else:
        log.warning("Deployment engine '%s' unavailable: %s", deployment_engine.name, detail)
    yield


app = FastAPI(title="AE3GIS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ORIGINS != ["*"],  # credentials + wildcard is invalid per spec
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topologies.router)
app.include_router(deployment.router)
app.include_router(catalog.router)
app.include_router(presets.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "engine": deployment_engine.name}
