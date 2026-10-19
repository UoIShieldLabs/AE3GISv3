"""An in-memory Docker Hub (hub API, auth, registry) behind an httpx MockTransport."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import httpx

from services.dockerhub import DockerHubClient

_INDEX = "application/vnd.oci.image.index.v1+json"
_MANIFEST = "application/vnd.oci.image.manifest.v1+json"


def _digest(*parts: str) -> str:
    return "sha256:" + hashlib.sha256("/".join(parts).encode()).hexdigest()


@dataclass
class FakeRepo:
    name: str
    description: str = "[ae3gis] test image"
    labels: dict[str, str] = field(default_factory=dict)
    tags: tuple[str, ...] = ("latest",)
    platforms: tuple[str, ...] = ("linux/amd64",)
    # Publish as an index with an attestation entry (what buildx pushes).
    index: bool = True
    private: bool = False
    # Bumped when the image changes (new digest).
    version: int = 1

    def manifest_digest(self, platform: str) -> str:
        return _digest(self.name, str(self.version), "manifest", platform)

    @property
    def config_digest(self) -> str:
        return _digest(self.name, str(self.version), "config")

    @property
    def top_digest(self) -> str:
        if self.index:
            return _digest(self.name, str(self.version), "index")
        return self.manifest_digest(self.platforms[0])


class FakeHub:
    def __init__(self, *, remaining: int | None = 100, page_size: int | None = None) -> None:
        self.namespaces: dict[str, dict[str, FakeRepo]] = {}
        self.remaining = remaining
        self.page_size = page_size
        self.manifest_gets = 0
        self.heads = 0

    def add(self, namespace: str, repo: str, **kw) -> FakeRepo:
        r = FakeRepo(repo, **kw)
        self.namespaces.setdefault(namespace, {})[repo] = r
        return r

    def client(self) -> DockerHubClient:
        return DockerHubClient(transport=httpx.MockTransport(self.handle))

    # ── routing ──
    def handle(self, request: httpx.Request) -> httpx.Response:
        host, path = request.url.host, request.url.path
        if host == "hub.docker.com":
            return self._hub(request, path.strip("/").split("/"))
        if host == "auth.docker.io":
            return httpx.Response(200, json={"token": "t"})
        if host == "registry-1.docker.io":
            return self._registry(request, path.strip("/").split("/"))
        return httpx.Response(404)

    def _hub(self, request: httpx.Request, parts: list[str]) -> httpx.Response:
        # v2/namespaces/<ns>/repositories[/<repo>/tags[/<tag>]]
        if len(parts) < 4 or parts[:2] != ["v2", "namespaces"] or parts[3] != "repositories":
            return httpx.Response(404)
        ns = self.namespaces.get(parts[2])
        if ns is None:
            return httpx.Response(404, json={"message": "not found"})
        if len(parts) == 4:
            repos = sorted(ns.values(), key=lambda r: r.name)
            size = self.page_size or 100
            page = int(request.url.params.get("page", "1"))
            chunk = repos[(page - 1) * size : page * size]
            more = page * size < len(repos)
            nxt = str(request.url.copy_set_param("page", str(page + 1))) if more else None
            return httpx.Response(
                200,
                json={
                    "count": len(repos),
                    "next": nxt,
                    "results": [
                        {"name": r.name, "description": r.description, "is_private": r.private}
                        for r in chunk
                    ],
                },
            )
        repo = ns.get(parts[4])
        if repo is None or len(parts) < 6 or parts[5] != "tags":
            return httpx.Response(404)
        if len(parts) == 7:
            if parts[6] not in repo.tags:
                return httpx.Response(404)
            return httpx.Response(200, json=self._tag(repo, parts[6]))
        # newest first: the order the tags tuple lists them
        return httpx.Response(200, json={"results": [self._tag(repo, t) for t in repo.tags]})

    @staticmethod
    def _tag(repo: FakeRepo, tag: str) -> dict:
        images = [
            {
                "os": p.split("/")[0],
                "architecture": p.split("/")[1],
                "variant": p.split("/")[2] if p.count("/") == 2 else None,
                "digest": repo.manifest_digest(p),
            }
            for p in repo.platforms
        ]
        if repo.index:
            images.append({"os": "unknown", "architecture": "unknown", "digest": "sha256:att"})
        return {"name": tag, "digest": repo.top_digest, "images": images}

    def _limit_headers(self) -> dict[str, str]:
        if self.remaining is None:
            return {}
        return {"ratelimit-remaining": f"{self.remaining};w=3600"}

    def _registry(self, request: httpx.Request, parts: list[str]) -> httpx.Response:
        # v2/<ns>/<repo>/(manifests|blobs)/<ref>
        if len(parts) != 5 or parts[0] != "v2":
            return httpx.Response(404)
        repo = self.namespaces.get(parts[1], {}).get(parts[2])
        if repo is None:
            return httpx.Response(404)
        kind, ref = parts[3], parts[4]
        if kind == "blobs":
            if ref != repo.config_digest:
                return httpx.Response(404)
            return httpx.Response(200, json={"config": {"Labels": dict(repo.labels)}})
        if request.method == "HEAD":
            self.heads += 1
            return httpx.Response(200, headers=self._limit_headers())
        if self.remaining is not None and self.remaining <= 0:
            return httpx.Response(429)
        self.manifest_gets += 1
        if self.remaining is not None:
            self.remaining -= 1
        if repo.index and ref in (repo.top_digest, *repo.tags):
            body = {
                "mediaType": _INDEX,
                "manifests": [
                    {
                        "digest": repo.manifest_digest(p),
                        "platform": {"os": p.split("/")[0], "architecture": p.split("/")[1]},
                    }
                    for p in repo.platforms
                ]
                + [
                    {
                        "digest": "sha256:att",
                        "platform": {"os": "unknown", "architecture": "unknown"},
                    }
                ],
            }
        else:
            body = {"mediaType": _MANIFEST, "config": {"digest": repo.config_digest}}
        return httpx.Response(200, content=json.dumps(body), headers=self._limit_headers())


def standard_labels(type_: str, **extra: str) -> dict[str, str]:
    """Labels of an image that follows the standard (``extra`` keys use '_' for '.')."""
    labels = {"io.ae3gis.schema": "1", "io.ae3gis.type": type_}
    for key, value in extra.items():
        labels["io.ae3gis." + key.replace("__", "-").replace("_", ".")] = value
    return labels
