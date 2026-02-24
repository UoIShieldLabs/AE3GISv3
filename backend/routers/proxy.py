import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import AuthIdentity, require_any_auth, validate_student_topology
from database import get_db
from models import Topology
from services import clab_manager

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

# We use a single shared httpx client for connection pooling
# Note: In a production app, you might want to manage this lifecycle in main.py events
http_client = httpx.AsyncClient(verify=False)

def _get_topo(topology_id: str, db: Session) -> Topology:
    topo = db.get(Topology, topology_id)
    if not topo:
        raise HTTPException(404, "Topology not found")
    return topo

@router.api_route("/{topology_id}/{container_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy_web_ui(
    request: Request,
    topology_id: str,
    container_id: str,
    path: str,
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
    # By default, we proxy to port 80. (In the future this could be expanded to support other ports)
    target_url = f"http://{target_ip}:80/{path}"
    
    # Forward the query parameters (except our auth token)
    query_params = dict(request.query_params)
    query_params.pop("token", None) # Remove the AE3GIS auth token from the forwarded request
    
    # 4. Proxy the request
    try:
        # We need to strip host headers that might confuse the target server
        excluded_headers = ["host", "content-length"]
        headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}
        
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
        
        return StreamingResponse(
            response.aiter_raw(),
            status_code=response.status_code,
            headers={k: v for k, v in response.headers.items() if k.lower() not in ["transfer-encoding"]},
            background=response.aclose
        )
        
    except httpx.RequestError as e:
        raise HTTPException(502, f"Failed to proxy request to container: {e}")
