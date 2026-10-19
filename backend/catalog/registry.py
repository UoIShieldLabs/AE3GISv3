"""Merge images loaded from registries into the built-in catalog.

Pure. A registry *snapshot* is what its last sync saw: per candidate repo (one
whose Docker Hub description carries the ``[ae3gis]`` marker) the tag read,
its digest and platforms, and the image's labels. Labels are parsed here, at
merge time, so a newer parser applies to stored snapshots without a re-sync.

Merging rules (``docs/image-standard.md``):

- an image whose ``io.ae3gis.type`` is a built-in type joins it as a variant;
  the built-in type's fields and default image win;
- a new type takes its fields from its image labelled ``io.ae3gis.default``
  (else the first repo by name), which must name it and give its role;
- a type a registry added earlier wins over a later registry's (whose images
  join it as variants);
- an image ref the built-in catalog already describes keeps that description.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from catalog.models import Catalog, CategorySpec, ImageSpec, NodeTypeSpec, RegistrySource
from domain.image_labels import (
    TYPE_NAME,
    TYPE_ROLE,
    ImageLabels,
    TypeMeta,
    parse_image_labels,
)

DEFAULT_COLOR = "#9ca3af"
DEFAULT_ICON = "default"


@dataclass
class Candidate:
    repo: str
    tag: str
    digest: str | None = None
    platforms: list[str] = field(default_factory=list)
    labels: dict[str, str] | None = None
    # Not inspected yet (the sync stopped short of Docker Hub's pull limit).
    pending: bool = False
    # Why its labels could not be read.
    error: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Candidate:
        return cls(
            repo=d["repo"],
            tag=d.get("tag") or "latest",
            digest=d.get("digest"),
            platforms=list(d.get("platforms") or []),
            labels=d.get("labels"),
            pending=bool(d.get("pending")),
            error=d.get("error"),
        )


@dataclass
class Snapshot:
    namespace: str
    candidates: list[Candidate]

    @classmethod
    def from_dict(cls, namespace: str, d: dict[str, Any] | None) -> Snapshot:
        return cls(namespace, [Candidate.from_dict(c) for c in (d or {}).get("candidates", [])])


@dataclass
class Report:
    """What a registry contributed, for the UI."""

    loaded: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class _Image:
    cand: Candidate
    ref: str
    labels: ImageLabels


def image_ref(namespace: str, cand: Candidate) -> str:
    return f"{namespace}/{cand.repo}:{cand.tag}"


def hub_category(namespace: str) -> str:
    """The category a registry's new types go in when they name none."""
    return f"hub:{namespace}"


def _title(category: str) -> str:
    return category.replace("-", " ").title()


def _image_spec(namespace: str, img: _Image) -> ImageSpec:
    lb = img.labels
    return ImageSpec(
        displayName=lb.title or img.cand.repo,
        description=lb.description or "",
        stability=lb.stability,  # type: ignore[arg-type]
        source=RegistrySource(registry=namespace),
        platforms=img.cand.platforms or None,
        shell=lb.shell,
        ownBridge=lb.own_bridge,
    )


def _type_spec(namespace: str, type_id: str, meta: TypeMeta, refs: list[str]) -> NodeTypeSpec:
    return NodeTypeSpec(
        displayName=meta.name or type_id,
        role=meta.role,  # type: ignore[arg-type]
        category=meta.category or hub_category(namespace),
        defaultImage=refs[0],
        images=refs,
        color=meta.color or DEFAULT_COLOR,
        label=meta.label or type_id.replace("-", "")[:4].upper(),
        icon=meta.icon or DEFAULT_ICON,
        description=meta.description or "",
        webUiPort=meta.web_ui_port,
        purdueLevel=meta.purdue_level,
        origin=namespace,
    )


def merge(base: Catalog, snapshots: list[Snapshot]) -> tuple[Catalog, dict[str, Report]]:
    """The catalog with every registry's images, and a report per registry.

    ``snapshots`` are in precedence order (the earliest-added registry first).
    """
    images: dict[str, ImageSpec] = dict(base.images)
    types: dict[str, NodeTypeSpec] = {k: v.model_copy(deep=True) for k, v in base.types.items()}
    categories: list[CategorySpec] = list(base.categories)
    reports: dict[str, Report] = {}

    for snap in snapshots:
        ns = snap.namespace
        report = reports[ns] = Report()
        by_type: dict[str, list[_Image]] = defaultdict(list)

        for cand in sorted(snap.candidates, key=lambda c: c.repo):
            if cand.pending:
                report.pending.append(cand.repo)
                continue
            if cand.error:
                report.rejected.append(
                    {"repo": cand.repo, "tag": cand.tag, "reasons": [cand.error]}
                )
                continue
            parsed = parse_image_labels(cand.labels)
            report.warnings += [f"{cand.repo}: {w}" for w in parsed.warnings]
            if parsed.image is None:
                report.rejected.append(
                    {"repo": cand.repo, "tag": cand.tag, "reasons": parsed.errors}
                )
                continue
            by_type[parsed.image.type].append(_Image(cand, image_ref(ns, cand), parsed.image))

        for type_id, members in by_type.items():
            existing = types.get(type_id)
            if existing is None:
                defaults = [m for m in members if m.labels.default]
                if len(defaults) > 1:
                    report.warnings.append(
                        f"type {type_id!r}: {len(defaults)} images say io.ae3gis.default; "
                        f"using {defaults[0].cand.repo}"
                    )
                head = defaults[0] if defaults else members[0]
                meta = head.labels.type_meta
                missing = [k for k, v in ((TYPE_NAME, meta.name), (TYPE_ROLE, meta.role)) if not v]
                if missing:
                    reason = (
                        f"type {type_id!r} is new, and its default image "
                        f"({head.cand.repo}) does not set {' and '.join(missing)}"
                    )
                    for m in members:
                        report.rejected.append(
                            {"repo": m.cand.repo, "tag": m.cand.tag, "reasons": [reason]}
                        )
                    continue
                for m in members:
                    if m is head:
                        continue
                    differ = {
                        k for k, v in m.labels.type_meta.given().items() if meta.given().get(k) != v
                    }
                    if differ:
                        report.warnings.append(
                            f"{m.cand.repo}: io.ae3gis.type.* differs from {head.cand.repo}'s "
                            f"({', '.join(sorted(differ))}); {head.cand.repo}'s is used"
                        )
                ordered = [head] + [m for m in members if m is not head]
                try:
                    types[type_id] = _type_spec(ns, type_id, meta, [m.ref for m in ordered])
                except ValueError as exc:
                    for m in members:
                        report.rejected.append(
                            {"repo": m.cand.repo, "tag": m.cand.tag, "reasons": [str(exc)]}
                        )
                    continue
                category = types[type_id].category
                if category not in {c.id for c in categories}:
                    label = ns if category == hub_category(ns) else _title(category)
                    categories.append(CategorySpec(id=category, label=label))
                new_type = True
            else:
                if existing.origin and existing.origin != ns:
                    report.warnings.append(
                        f"type {type_id!r} comes from registry {existing.origin}; "
                        f"this registry's images join it as variants"
                    )
                for m in members:
                    if m.ref not in existing.images:
                        existing.images.append(m.ref)
                new_type = False

            for m in members:
                if m.ref in base.images:
                    report.warnings.append(
                        f"{m.cand.repo}: {m.ref} is described by the built-in catalog; "
                        "its labels are ignored"
                    )
                else:
                    images[m.ref] = _image_spec(ns, m)
                report.loaded.append(
                    {
                        "ref": m.ref,
                        "repo": m.cand.repo,
                        "tag": m.cand.tag,
                        "type": type_id,
                        "name": images[m.ref].displayName,
                        "platforms": m.cand.platforms,
                        "new_type": new_type,
                    }
                )

    merged = base.model_copy(update={"images": images, "types": types, "categories": categories})
    return merged, reports
