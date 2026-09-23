"""Typed shape of ``node_types.json`` (catalog schema version 2).

The catalog is one of the two cross-tier contracts (with the API envelope), so
it is modelled here and served with a response model: the frontend's catalog
types are generated from OpenAPI rather than written by hand.

- ``categories`` order the palette.
- ``types`` are what a user places; each lists its interchangeable ``images``
  (its *variants*) and a ``defaultImage``.
- ``images`` describes images by ref. A ref missing from it is pulled from a
  registry as before; one with a ``build`` source is built by AE3GIS from a
  Dockerfile in one of the ``sources``.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal["router", "switch", "host"]
Stability = Literal["stable", "experimental", "hidden"]


def _relative_path(value: str, what: str) -> str:
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"{what} must be a relative path inside the source: {value!r}")
    return value


class CategorySpec(BaseModel):
    id: str
    label: str


class GitSource(BaseModel):
    """A git repository the backend clones (and syncs on demand)."""

    kind: Literal["git"]
    url: str
    ref: str = "main"


class PathSource(BaseModel):
    """A directory on the backend's filesystem (e.g. a mounted checkout)."""

    kind: Literal["path"]
    path: str


SourceSpec = Annotated[GitSource | PathSource, Field(discriminator="kind")]


class BuildSource(BaseModel):
    """Build the image from ``<source>/<context>/<dockerfile>``."""

    kind: Literal["build"]
    repo: str
    context: str
    dockerfile: str = "Dockerfile"
    args: dict[str, str] = Field(default_factory=dict)

    @field_validator("context")
    @classmethod
    def _context(cls, v: str) -> str:
        return _relative_path(v, "context")

    @field_validator("dockerfile")
    @classmethod
    def _dockerfile(cls, v: str) -> str:
        return _relative_path(v, "dockerfile")


class RegistrySource(BaseModel):
    """Pull the image by ref from a registry (the default)."""

    kind: Literal["registry"] = "registry"


ImageSource = Annotated[BuildSource | RegistrySource, Field(discriminator="kind")]


class ImageSpec(BaseModel):
    displayName: str
    description: str = ""
    stability: Stability = "stable"
    source: ImageSource = Field(default_factory=RegistrySource)
    # Docker platforms the image builds for (e.g. "linux/amd64"); None = any.
    platforms: list[str] | None = None


class NodeTypeSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    displayName: str
    role: Role
    category: str
    defaultImage: str
    # Interchangeable images for this type (its variants), default included.
    images: list[str] = Field(default_factory=list)
    color: str
    label: str
    icon: str
    description: str = ""
    webUiPort: int | None = None
    purdueLevel: float | None = None

    @model_validator(mode="after")
    def _default_is_a_variant(self) -> NodeTypeSpec:
        if not self.images:
            self.images = [self.defaultImage]
        elif self.defaultImage not in self.images:
            raise ValueError(f"defaultImage {self.defaultImage!r} is not one of its images")
        return self


class Catalog(BaseModel):
    version: int
    description: str = ""
    defaults: dict[str, str]
    categories: list[CategorySpec] = Field(default_factory=list)
    sources: dict[str, SourceSpec] = Field(default_factory=dict)
    images: dict[str, ImageSpec] = Field(default_factory=dict)
    types: dict[str, NodeTypeSpec]

    @model_validator(mode="after")
    def _consistent(self) -> Catalog:
        if not self.types:
            raise ValueError("the catalog must define at least one node type")
        if not self.defaults.get("host_image"):
            raise ValueError("defaults.host_image is required as the fallback image")
        category_ids = {c.id for c in self.categories}
        for ref, image in self.images.items():
            if isinstance(image.source, BuildSource) and image.source.repo not in self.sources:
                raise ValueError(f"image {ref!r} builds from unknown source {image.source.repo!r}")
        for name, spec in self.types.items():
            if category_ids and spec.category not in category_ids:
                raise ValueError(f"type {name!r} has unknown category {spec.category!r}")
            default = self.images.get(spec.defaultImage)
            if default is not None and default.stability == "hidden":
                raise ValueError(f"type {name!r} defaults to hidden image {spec.defaultImage!r}")
        return self
