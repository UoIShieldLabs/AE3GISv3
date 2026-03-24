import asyncio
import logging
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import AuthIdentity, PROXY_AUTH_COOKIE, require_any_auth, validate_student_topology
from database import get_db
from models import Topology
from services import clab_manager

log = logging.getLogger(__name__)
PROXY_PORT_COOKIE = "ae3gis_proxy_port"

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

# We use a single shared httpx client for connection pooling
# Note: In a production app, you might want to manage this lifecycle in main.py events
http_client = httpx.AsyncClient(verify=False)

def _get_topo(topology_id: str, db: Session) -> Topology:
    topo = db.get(Topology, topology_id)
    if not topo:
        raise HTTPException(404, "Topology not found")
    return topo


def _proxy_prefix(request: Request, topology_id: str, container_id: str) -> str:
    root = str(request.base_url).rstrip("/")
    return f"{root}/api/proxy/{topology_id}/{container_id}"


def _rewrite_html_body(html: str, proxy_prefix: str) -> str:
    rewritten = html
    for attr in ("href", "src", "action"):
        rewritten = re.sub(
            rf'({attr}\s*=\s*["\'])/(?!/)',
            rf"\1{proxy_prefix}/",
            rewritten,
            flags=re.IGNORECASE,
        )

    shim = f"""
<script>
(() => {{
  const PROXY_PREFIX = {proxy_prefix!r};
  const rewrite = (value) => {{
    if (typeof value !== 'string') return value;
    if (value.startsWith('//')) return value;
    if (value.startsWith('/')) return PROXY_PREFIX + value;
    return value;
  }};

  const origFetch = window.fetch;
  if (origFetch) {{
    window.fetch = (input, init) => {{
      if (typeof input === 'string') return origFetch(rewrite(input), init);
      if (input instanceof Request) return origFetch(new Request(rewrite(input.url), input), init);
      return origFetch(input, init);
    }};
  }}

  const origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {{
    return origOpen.call(this, method, rewrite(url), ...rest);
  }};

  const origSend = HTMLFormElement.prototype.submit;
  HTMLFormElement.prototype.submit = function() {{
    if (this.action) this.action = rewrite(this.action);
    return origSend.call(this);
  }};

  document.addEventListener('submit', (event) => {{
    const form = event.target;
    if (form && form.action) form.action = rewrite(form.action);
  }}, true);
}})();
</script>
"""
    if "</head>" in rewritten:
        return rewritten.replace("</head>", f"{shim}</head>", 1)
    if "<body" in rewritten:
        return rewritten.replace("<body", f"{shim}<body", 1)
    return shim + rewritten


def _rewrite_location(location: str, request: Request, topology_id: str, container_id: str, port: int) -> str:
    parsed = urlsplit(location)
    path_prefix = f"/api/proxy/{topology_id}/{container_id}"
    token = request.query_params.get("token")

    def _with_proxy_params(path: str, query: str) -> str:
        params = dict(parse_qsl(query, keep_blank_values=True))
        params.setdefault("port", str(port))
        if token:
            params.setdefault("token", token)
        encoded = urlencode(params)
        return f"{path_prefix}{path}" + (f"?{encoded}" if encoded else "")

    if parsed.scheme and parsed.netloc:
        return _with_proxy_params(parsed.path or "/", parsed.query)

    if location.startswith("/"):
        return _with_proxy_params(parsed.path or "/", parsed.query)

    return location

@router.api_route("/{topology_id}/{container_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy_web_ui(
    request: Request,
    topology_id: str,
    container_id: str,
    path: str,
    port: int | None = Query(default=None, ge=1, le=65535),
):
    """
    Acts as a reverse proxy, forwarding requests from the user's browser directly
    to the internal Docker IP of the specified Containerlab node.
    
    The frontend should call this like:
    /api/proxy/{topology_id}/{container_id}/index.html?token=...
    """
    # 1. Authorize the user has access to this specific topology
    db: Session = next(get_db())
    try:
        authorization = request.headers.get("authorization")
        identity = require_any_auth(request=request, authorization=authorization, db=db)
        validate_student_topology(identity, topology_id)
        
        topo = _get_topo(topology_id, db)
        if topo.status != "deployed":
            raise HTTPException(409, "Topology is not currently deployed")
            
        topo_name = clab_manager.deployment_name(topo.id, topo.data)
        docker_name = f"clab-{topo_name}-{container_id}"
    finally:
        db.close() # Close DB connection prevent pool exhaustion during streaming


    cookie_port_raw = request.cookies.get(PROXY_PORT_COOKIE)
    if port is None and cookie_port_raw:
        try:
            cookie_port = int(cookie_port_raw)
            if 1 <= cookie_port <= 65535:
                port = cookie_port
        except ValueError:
            pass
    if port is None:
        port = 80

    # 2. Look up the internal Docker IP of the target container via docker inspect.
    #    We query Docker directly instead of going through `containerlab inspect`
    #    because the latter requires sudo which may not be available to the backend.
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "inspect",
            "--format", "{{.State.Running}}|{{range .NetworkSettings.Networks}}{{.IPAddress}}|{{end}}",
            docker_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    except Exception as e:
        raise HTTPException(500, f"Failed to inspect container: {e}")

    if proc.returncode != 0:
        detail = stderr.decode(errors="replace").strip()
        log.warning("docker inspect %s failed: %s", docker_name, detail)
        raise HTTPException(404, f"Container {container_id} not found in deployment")

    parts = stdout.decode().strip().split("|")
    is_running = parts[0].lower() == "true" if parts else False
    # IPs are in parts[1:], filter out empty strings
    ips = [p for p in parts[1:] if p]

    if not is_running:
        raise HTTPException(409, f"Container {container_id} is not running")

    target_ip = ips[0] if ips else None
    if not target_ip:
        raise HTTPException(502, f"Container {container_id} does not have a valid management IP")

    # 3. Construct the target URL
    target_url = f"http://{target_ip}:{port}/{path}"
    
    # Forward the query parameters (except our auth token)
    query_params = dict(request.query_params)
    query_params.pop("token", None) # Remove the AE3GIS auth token from the forwarded request
    query_params.pop("port", None)
    
    # 4. Proxy the request
    try:
        # Only forward headers that the target app needs; strip auth,
        # proxy, and host headers that confuse simple web servers like Werkzeug.
        _pass_through = {"accept", "accept-language", "accept-encoding",
                         "content-type", "user-agent", "referer", "origin",
                         "cache-control", "pragma", "if-none-match",
                         "if-modified-since", "cookie"}
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() in _pass_through}
        headers["host"] = f"{target_ip}:{port}"
        
        # We use httpx to stream the response back.
        # This handles large files (like images or video) without buffering everything in memory.
        req = http_client.build_request(
            method=request.method,
            url=target_url,
            params=query_params,
            headers=headers,
            content=request.stream(),
        )
        
        # We don't await the full response body, we stream it
        response = await http_client.send(req, stream=True)
        
        response_headers = {
            k: v for k, v in response.headers.items() if k.lower() not in ["transfer-encoding", "location", "content-length", "set-cookie"]
        }
        location = response.headers.get("location")
        if location:
            response_headers["location"] = _rewrite_location(location, request, topology_id, container_id, port)
        content_type = response.headers.get("content-type", "")
        proxy_prefix = f"/api/proxy/{topology_id}/{container_id}"
        if "text/html" in content_type.lower():
            body = await response.aread()
            await response.aclose()
            text = body.decode(response.encoding or "utf-8", errors="replace")
            rewritten = _rewrite_html_body(text, proxy_prefix)
            proxy_response = Response(
                content=rewritten,
                status_code=response.status_code,
                headers=response_headers,
                media_type=content_type,
            )
        else:
            proxy_response = StreamingResponse(
                response.aiter_raw(),
                status_code=response.status_code,
                headers=response_headers,
                background=response.aclose
            )
        # Forward Set-Cookie headers from target, rewriting Path to proxy prefix
        proxy_path = f"/api/proxy/{topology_id}/{container_id}"
        for raw_cookie in response.headers.get_list("set-cookie"):
            rewritten_cookie = re.sub(
                r"(?i)(;\s*path=)/[^;]*",
                rf"\g<1>{proxy_path}",
                raw_cookie,
            )
            if not re.search(r"(?i);\s*path=", rewritten_cookie):
                rewritten_cookie += f"; Path={proxy_path}"
            proxy_response.headers.append("set-cookie", rewritten_cookie)

        token = request.query_params.get("token") or request.cookies.get(PROXY_AUTH_COOKIE)
        if token:
            proxy_response.set_cookie(
                key=PROXY_AUTH_COOKIE,
                value=token,
                httponly=True,
                samesite="lax",
                path=proxy_path,
            )
        proxy_response.set_cookie(
            key=PROXY_PORT_COOKIE,
            value=str(port),
            httponly=True,
            samesite="lax",
            path=proxy_path,
        )
        return proxy_response
        
    except httpx.RequestError as e:
        raise HTTPException(502, f"Failed to proxy request to container: {e}")
