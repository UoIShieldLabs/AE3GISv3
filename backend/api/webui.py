"""Relay a lab node's own web UI to the browser.

A node's HTTP view (e.g. the process simulator's status page, an HMI console)
lives on an IP inside the Kathará lab, which the backend can't reach directly —
it only has the Docker socket. So the backend ``docker exec``s a buffered
``curl`` against ``127.0.0.1:<port>`` *inside the node* and relays the response.
This rides the existing ``/api`` proxy, needs no host ports or extra container,
and keeps the lab isolated. It suits server-rendered pages (what the ICS images
serve); a full port-forward proxy for complex apps is a later upgrade.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

import catalog
from api.deps import get_db, get_engine
from api.errors import Conflict, Invalid, NotFound
from auth import require_any_auth, require_instructor
from domain.topology import find_container
from engine.base import DeploymentEngine, EngineState
from services import topologies

router = APIRouter(prefix="/api/v1", tags=["webui"])

# Response headers we recompute or that don't survive the relay.
_DROP_HEADERS = {"content-length", "transfer-encoding", "connection", "content-encoding"}
_MAX_BYTES = 8_000_000


def _resolve_port(topo, node_id: str) -> int:
    container = find_container(topo.data or {}, node_id)
    if container is None:
        raise NotFound("Device")
    port = container.get("webUiPort")
    if not isinstance(port, int):
        port = catalog.web_ui_port(str(container.get("type", "")))
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise Invalid(
            "This device has no web UI port; set one in the inspector",
            code="no_web_ui",
            node=node_id,
        )
    return port


def _prefix(topology_id: str, node_id: str) -> str:
    return f"/api/v1/topologies/{topology_id}/webui/{node_id}/"


def _rewrite_html(body: bytes, prefix: str) -> bytes:
    """Make the page load back through the relay: a <base> for relative URLs,
    and root-absolute src/href/action rewritten to the relay prefix."""
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body
    # Root-absolute URLs ignore <base>, so point them at the relay prefix too
    # (prefix ends in "/", so `src="/x"` -> `src="<prefix>x"`). Do this before
    # injecting <base> so the base tag's own href is not rewritten.
    for attr in ("src", "href", "action"):
        for quote in ('"', "'"):
            text = text.replace(f"{attr}={quote}/", f"{attr}={quote}{prefix}")
    base = f'<base href="{prefix}">'
    i = text.lower().find("<head>")
    text = text[: i + 6] + base + text[i + 6 :] if i != -1 else base + text
    return text.encode("utf-8")


def _rewrite_location(loc: str, prefix: str, port: int) -> str:
    """Re-root a redirect's ``Location`` through the relay, mirroring
    ``_rewrite_html``: a root-absolute ``Location: /`` would otherwise send the
    browser to the backend origin, not back into the node's web UI. Relative
    targets already resolve against the relayed request URL, so leave them be."""
    for host in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
        if loc.startswith(host):  # an internal absolute URL -> keep only its path
            loc = loc[len(host) :] or "/"
            break
    if loc.startswith("/") and not loc.startswith("//"):
        return prefix + loc[1:]  # prefix ends in "/", so "/" -> prefix, "/x" -> prefix+"x"
    return loc


def _parse_response(raw: bytes) -> tuple[int, dict[str, str], bytes]:
    sep = raw.find(b"\r\n\r\n")
    nl = b"\r\n"
    if sep == -1:
        sep, nl = raw.find(b"\n\n"), b"\n"
    if sep == -1:
        return 502, {}, raw
    head, body = raw[:sep], raw[sep + len(nl) * 2 :]
    lines = head.split(nl)
    status = 200
    parts = lines[0].split(b" ")
    if len(parts) >= 2 and parts[1].isdigit():
        status = int(parts[1])
    headers: dict[str, str] = {}
    for line in lines[1:]:
        k, _, v = line.partition(b":")
        key = k.decode("latin-1").strip().lower()
        if key and key not in _DROP_HEADERS:
            headers[key] = v.decode("latin-1").strip()
    return status, headers, body


async def _relay(
    request: Request,
    topology_id: str,
    node_id: str,
    path: str,
    db: Session,
    engine: DeploymentEngine,
) -> Response:
    topo = topologies.get_or_404(db, topology_id)
    if topo.status != "deployed" or not topo.engine_state:
        raise Conflict(
            "Deploy the topology to view a node's web UI", code="bad_state", status=topo.status
        )
    state = EngineState.from_dict(topo.engine_state)
    port = _resolve_port(topo, node_id)
    query = f"?{request.url.query}" if request.url.query else ""
    url = f"http://127.0.0.1:{port}/{path}{query}"
    argv = ["curl", "-s", "-i", "--max-time", "8", "-X", request.method, url]
    if request.method != "GET":
        body = await request.body()
        ctype = request.headers.get("content-type")
        if ctype:
            argv += ["-H", f"Content-Type: {ctype}"]
        if body:
            argv += ["--data-binary", body.decode("latin-1")]
    try:
        code, out, _err = await engine.exec_output(state, node_id, argv, timeout=10.0)
    except LookupError as exc:
        raise Conflict(str(exc), code="node_gone", status=topo.status) from exc
    if code != 0 and not out:
        raise Conflict(
            f"The web UI on {node_id} did not respond (is its service up?)", code="no_response"
        )
    status, headers, resp_body = _parse_response(out[:_MAX_BYTES])
    ctype = headers.get("content-type", "application/octet-stream")
    if "text/html" in ctype:
        resp_body = _rewrite_html(resp_body, _prefix(topology_id, node_id))
    if 300 <= status < 400 and "location" in headers:
        headers["location"] = _rewrite_location(
            headers["location"], _prefix(topology_id, node_id), port
        )
    headers.pop("content-type", None)
    return Response(content=resp_body, status_code=status, media_type=ctype, headers=headers)


@router.get("/topologies/{topology_id}/webui/{node_id}")
def webui_root(topology_id: str, node_id: str, _=Depends(require_any_auth)):
    return RedirectResponse(url=_prefix(topology_id, node_id))


@router.get("/topologies/{topology_id}/webui/{node_id}/{path:path}")
async def webui_get(
    topology_id: str,
    node_id: str,
    path: str,
    request: Request,
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    _=Depends(require_any_auth),
):
    """Relay a GET to the node's web UI (the page, its assets)."""
    return await _relay(request, topology_id, node_id, path, db, engine)


@router.post("/topologies/{topology_id}/webui/{node_id}/{path:path}")
async def webui_post(
    topology_id: str,
    node_id: str,
    path: str,
    request: Request,
    db: Session = Depends(get_db),
    engine: DeploymentEngine = Depends(get_engine),
    _=Depends(require_instructor),
):
    """Relay a POST to the node's web UI (e.g. an HMI's open/close button)."""
    return await _relay(request, topology_id, node_id, path, db, engine)
