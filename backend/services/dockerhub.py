"""A small Docker Hub client: list a namespace, pick a tag, read an image's labels.

Two APIs, with different costs:

- ``hub.docker.com/v2`` lists repositories and tags (digests and platforms
  included). It has its own request budget and does not count as pulls.
- ``registry-1.docker.io/v2`` serves manifests and blobs. Reading labels means
  GETting a manifest (and, for a multi-platform index, the platform's one),
  which Docker Hub counts as **one pull** against the IP's limit (anonymous:
  100/hour). Blob GETs and manifest HEADs are free; a HEAD tells how many
  pulls are left (``ratelimit-remaining``).

Everything is anonymous: private repositories are skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from domain.image_labels import relevant

HUB = "https://hub.docker.com"
REGISTRY = "https://registry-1.docker.io"
AUTH = "https://auth.docker.io/token"

_NAMESPACE = re.compile(r"[a-z0-9][a-z0-9_-]{1,254}")
_HUB_HOSTS = {"hub.docker.com", "www.hub.docker.com"}
_REGISTRY_HOSTS = {"docker.io", "index.docker.io", "registry-1.docker.io"}
_MANIFEST_TYPES = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)
# Pages of 100 repositories read at most (a namespace bigger than this is cut).
_MAX_PAGES = 50


class HubError(RuntimeError):
    """Docker Hub answered with an error, or could not be reached."""


class NamespaceNotFound(HubError):
    pass


class RateLimited(HubError):
    """Docker Hub refused a manifest read: the pull limit is used up."""


def parse_hub_url(text: str) -> str:
    """The Docker Hub namespace a URL (or a bare name) points at.

    Accepts ``https://hub.docker.com/u/<ns>``, ``/orgs/<ns>``, ``/r/<ns>/<repo>``,
    ``/repositories/<ns>``, ``docker.io/<ns>`` and ``<ns>``. Raises ``ValueError``.
    """
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Enter a Docker Hub URL or namespace")
    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    host = (parsed.hostname or "").lower()
    parts = [p for p in parsed.path.split("/") if p]
    if host in _HUB_HOSTS:
        if len(parts) >= 2 and parts[0] in ("u", "orgs", "r", "repositories", "namespaces"):
            name = parts[1]
        else:
            raise ValueError(
                f"Not a Docker Hub namespace URL: {raw!r} (expected hub.docker.com/u/<namespace>)"
            )
    elif host in _REGISTRY_HOSTS:
        if not parts:
            raise ValueError(f"No namespace in {raw!r}")
        name = parts[0]
    elif "://" not in raw and "/" not in raw and "." not in raw:
        name = raw
    else:
        raise ValueError(f"Only Docker Hub is supported: {raw!r}")
    name = name.lower()
    if name == "_" or not _NAMESPACE.fullmatch(name):
        raise ValueError(f"Not a Docker Hub namespace: {name!r}")
    return name


def hub_url(namespace: str) -> str:
    return f"{HUB}/u/{namespace}"


@dataclass
class Repo:
    name: str
    description: str = ""
    private: bool = False


@dataclass
class Tag:
    name: str
    digest: str | None
    platforms: list[str] = field(default_factory=list)


@dataclass
class Labels:
    labels: dict[str, str]
    # Pulls left in Docker Hub's window after this read (None: not reported).
    remaining: int | None


def _remaining(response: httpx.Response) -> int | None:
    value = response.headers.get("ratelimit-remaining")
    if not value:
        return None
    try:
        return int(value.split(";", 1)[0])
    except ValueError:
        return None


def _platforms(images: list[dict]) -> list[str]:
    out = set()
    for img in images or []:
        os_, arch = img.get("os"), img.get("architecture")
        if not os_ or not arch or "unknown" in (os_, arch):
            continue  # an attestation manifest, not an image
        variant = img.get("variant")
        out.add(f"{os_}/{arch}" + (f"/{variant}" if variant else ""))
    return sorted(out)


def _platform_of(entry: dict) -> str | None:
    p = entry.get("platform") or {}
    os_, arch = p.get("os"), p.get("architecture")
    if not os_ or not arch or "unknown" in (os_, arch):
        return None
    return f"{os_}/{arch}" + (f"/{p['variant']}" if p.get("variant") else "")


class DockerHubClient:
    """Use as ``async with DockerHubClient() as hub``; ``transport`` is for tests."""

    def __init__(
        self, *, timeout: float = 20, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._timeout = timeout
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._tokens: dict[str, str] = {}

    async def __aenter__(self) -> DockerHubClient:
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            transport=self._transport,
            follow_redirects=True,
            headers={"User-Agent": "ae3gis"},
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(self, url: str, **kw) -> httpx.Response:
        assert self._client is not None, "use DockerHubClient as an async context manager"
        try:
            return await self._client.get(url, **kw)
        except httpx.HTTPError as exc:
            raise HubError(f"Docker Hub unreachable: {exc}") from exc

    @staticmethod
    def _check(response: httpx.Response, what: str) -> None:
        if response.status_code == 429:
            raise RateLimited(f"Docker Hub rate limit reached ({what})")
        if response.status_code >= 400:
            raise HubError(f"Docker Hub answered {response.status_code} for {what}")

    # ── hub.docker.com ──
    async def repositories(self, namespace: str) -> list[Repo]:
        url: str | None = f"{HUB}/v2/namespaces/{namespace}/repositories?page_size=100"
        repos: list[Repo] = []
        for _ in range(_MAX_PAGES):
            if not url:
                break
            r = await self._get(url)
            if r.status_code == 404:
                raise NamespaceNotFound(f"Docker Hub has no namespace {namespace!r}")
            self._check(r, f"the repositories of {namespace}")
            data = r.json()
            for item in data.get("results") or []:
                repos.append(
                    Repo(
                        name=item["name"],
                        description=item.get("description") or "",
                        private=bool(item.get("is_private")),
                    )
                )
            url = data.get("next")
        return repos

    async def pick_tag(self, namespace: str, repo: str) -> Tag | None:
        """``latest`` if the repo has it, else its most recently pushed tag."""
        base = f"{HUB}/v2/namespaces/{namespace}/repositories/{repo}/tags"
        r = await self._get(f"{base}/latest")
        if r.status_code == 404:
            r = await self._get(base, params={"page_size": 1, "ordering": "last_updated"})
            self._check(r, f"the tags of {namespace}/{repo}")
            results = r.json().get("results") or []
            if not results:
                return None
            item = results[0]
        else:
            self._check(r, f"{namespace}/{repo}:latest")
            item = r.json()
        images = item.get("images") or []
        digest = item.get("digest") or (images[0].get("digest") if len(images) == 1 else None)
        return Tag(name=item["name"], digest=digest, platforms=_platforms(images))

    # ── registry-1.docker.io ──
    async def _token(self, namespace: str, repo: str) -> str:
        scope = f"{namespace}/{repo}"
        if scope not in self._tokens:
            r = await self._get(
                AUTH,
                params={"service": "registry.docker.io", "scope": f"repository:{scope}:pull"},
            )
            self._check(r, f"a token for {scope}")
            self._tokens[scope] = r.json()["token"]
        return self._tokens[scope]

    async def _manifest(self, namespace: str, repo: str, reference: str) -> httpx.Response:
        token = await self._token(namespace, repo)
        r = await self._get(
            f"{REGISTRY}/v2/{namespace}/{repo}/manifests/{reference}",
            headers={"Authorization": f"Bearer {token}", "Accept": _MANIFEST_TYPES},
        )
        self._check(r, f"the manifest of {namespace}/{repo}")
        return r

    async def remaining(self, namespace: str, repo: str, reference: str) -> int | None:
        """Pulls left, from a manifest HEAD (which Docker Hub does not count)."""
        assert self._client is not None
        token = await self._token(namespace, repo)
        try:
            r = await self._client.head(
                f"{REGISTRY}/v2/{namespace}/{repo}/manifests/{reference}",
                headers={"Authorization": f"Bearer {token}", "Accept": _MANIFEST_TYPES},
            )
        except httpx.HTTPError as exc:
            raise HubError(f"Docker Hub unreachable: {exc}") from exc
        return _remaining(r)

    async def labels(self, namespace: str, repo: str, reference: str, prefer: list[str]) -> Labels:
        """The image's standard labels (one pull). For a multi-platform index,
        the first platform in ``prefer`` it has, else its first real one."""
        r = await self._manifest(namespace, repo, reference)
        remaining = _remaining(r)
        manifest = r.json()
        if "manifests" in manifest:
            entries = [(e, _platform_of(e)) for e in manifest["manifests"]]
            entries = [(e, p) for e, p in entries if p]
            if not entries:
                raise HubError(f"{namespace}/{repo}: the index lists no image")
            chosen = next((e for want in prefer for e, p in entries if p == want), entries[0][0])
            r = await self._manifest(namespace, repo, chosen["digest"])
            remaining = _remaining(r) if _remaining(r) is not None else remaining
            manifest = r.json()
        config = (manifest.get("config") or {}).get("digest")
        if not config:
            raise HubError(f"{namespace}/{repo}: the manifest has no config")
        token = await self._token(namespace, repo)
        blob = await self._get(
            f"{REGISTRY}/v2/{namespace}/{repo}/blobs/{config}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self._check(blob, f"the config of {namespace}/{repo}")
        labels = ((blob.json().get("config") or {}).get("Labels")) or {}
        return Labels(labels=relevant(labels), remaining=remaining)
