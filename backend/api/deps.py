"""FastAPI dependencies resolving per-app state (settings, DB, engine, runner)."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from config import Settings
from engine.base import DeploymentEngine
from services.artifacts import ArtifactStore
from services.images import ImageManager
from services.jobs import JobRunner
from services.live import LiveHub


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    db: Session = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def get_engine(request: Request) -> DeploymentEngine:
    return request.app.state.engine


def get_runner(request: Request) -> JobRunner:
    return request.app.state.runner


def get_images(request: Request) -> ImageManager:
    return request.app.state.images


def get_artifacts(request: Request) -> ArtifactStore:
    return request.app.state.artifacts


def get_live(request: Request) -> LiveHub:
    return request.app.state.live
