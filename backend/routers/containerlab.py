import asyncio
import contextlib
import logging
import os
import pty

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from database import get_db
from models import Topology
from services import clab_generator, clab_manager

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/topologies", tags=["containerlab"])


# ── Helpers ─────────────────────────────────────────────────────────


def _get_topo(topology_id: str, db: Session) -> Topology:
    topo = db.get(Topology, topology_id)
    if not topo:
        raise HTTPException(404, "Topology not found")
    return topo


def _topo_name(topo: Topology) -> str:
    """Return the clab topology name (used for inspect)."""
    return topo.data.get("name") or "ae3gis-topology"


# ── Generate ────────────────────────────────────────────────────────


@router.post("/{topology_id}/generate")
def generate(topology_id: str, db: Session = Depends(get_db)):
    topo = _get_topo(topology_id, db)
    yaml_str = clab_generator.generate_clab_yaml(topo.data)
    clab_manager.write_yaml(topology_id, yaml_str)

    topo.clab_yaml = yaml_str
    db.commit()

    return {"yaml": yaml_str}


# ── Deploy ──────────────────────────────────────────────────────────


@router.post("/{topology_id}/deploy")
async def deploy(topology_id: str, db: Session = Depends(get_db)):
    topo = _get_topo(topology_id, db)

    # Always regenerate YAML from current topology data
    yaml_str = clab_generator.generate_clab_yaml(topo.data)
    clab_manager.write_yaml(topology_id, yaml_str)
    topo.clab_yaml = yaml_str

    try:
        output = await clab_manager.deploy(topology_id)
        topo.status = "deployed"
        db.commit()
        return {"status": "deployed", "output": output}
    except (FileNotFoundError, RuntimeError) as e:
        topo.status = "error"
        db.commit()
        raise HTTPException(500, str(e))


# ── Destroy ─────────────────────────────────────────────────────────


@router.post("/{topology_id}/destroy")
async def destroy(topology_id: str, db: Session = Depends(get_db)):
    topo = _get_topo(topology_id, db)

    try:
        output = await clab_manager.destroy(topology_id)
        topo.status = "idle"
        db.commit()
        return {"status": "destroyed", "output": output}
    except (FileNotFoundError, RuntimeError) as e:
        topo.status = "error"
        db.commit()
        raise HTTPException(500, str(e))


# ── Status (single request) ────────────────────────────────────────


@router.get("/{topology_id}/status")
async def status(topology_id: str, db: Session = Depends(get_db)):
    topo = _get_topo(topology_id, db)
    containers = await clab_manager.inspect(_topo_name(topo))
    return {"status": topo.status, "containers": containers}


# ── Status (WebSocket stream) ──────────────────────────────────────


@router.websocket("/ws/{topology_id}/status")
async def status_stream(websocket: WebSocket, topology_id: str):
    db = next(get_db())
    try:
        topo = db.get(Topology, topology_id)
        if not topo:
            await websocket.close(code=4004, reason="Topology not found")
            return

        await websocket.accept()
        topo_name = _topo_name(topo)

        while True:
            containers = await clab_manager.inspect(topo_name)
            await websocket.send_json({
                "status": topo.status,
                "containers": containers,
            })
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    finally:
        db.close()


# ── Interactive exec terminal ──────────────────────────────────


@router.websocket("/ws/{topology_id}/exec/{container_id}")
async def exec_terminal(websocket: WebSocket, topology_id: str, container_id: str):
    """Attach an interactive /bin/sh session inside a deployed container via PTY."""
    db = next(get_db())
    proc = None
    master_fd = -1
    try:
        topo = db.get(Topology, topology_id)
        await websocket.accept()
        if not topo:
            await websocket.send_text("Error: Topology not found\r\n")
            await websocket.close(code=4004)
            return

        topo_name = topo.data.get("name") or "ae3gis-topology"
        docker_name = f"clab-{topo_name}-{container_id}"

        await websocket.send_text(f"Connecting to {docker_name}...\r\n")

        # Allocate a PTY pair — pass the slave end to the subprocess so that
        # `docker exec -it` sees a real TTY on its stdin and doesn't error out.
        master_fd, slave_fd = pty.openpty()
        try:
            proc = await asyncio.create_subprocess_exec(
                "sudo", "docker", "exec", "-it", docker_name, "/bin/sh",
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
            )
        except Exception as exc:
            await websocket.send_text(f"Error starting exec: {exc}\r\n")
            await websocket.close()
            return
        finally:
            os.close(slave_fd)  # Parent only communicates via master_fd

        loop = asyncio.get_running_loop()
        read_queue: asyncio.Queue[bytes] = asyncio.Queue()

        def _on_readable() -> None:
            try:
                data = os.read(master_fd, 4096)
                read_queue.put_nowait(data if data else b"")
            except OSError:
                read_queue.put_nowait(b"")
                loop.remove_reader(master_fd)

        loop.add_reader(master_fd, _on_readable)

        async def _read_pty() -> None:
            while True:
                data = await read_queue.get()
                if not data:
                    break
                try:
                    await websocket.send_text(data.decode(errors="replace"))
                except Exception:
                    break

        async def _write_pty() -> None:
            while True:
                try:
                    message = await websocket.receive_text()
                    os.write(master_fd, message.encode())
                except WebSocketDisconnect:
                    break
                except Exception:
                    break

        read_task = asyncio.create_task(_read_pty())
        write_task = asyncio.create_task(_write_pty())
        try:
            await asyncio.wait([read_task, write_task], return_when=asyncio.FIRST_COMPLETED)
        finally:
            loop.remove_reader(master_fd)
            read_task.cancel()
            write_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await read_task
            with contextlib.suppress(asyncio.CancelledError):
                await write_task

        # Send a clean close so the browser gets onclose instead of onerror
        with contextlib.suppress(Exception):
            await websocket.send_text("\r\n[session ended]\r\n")
            await websocket.close()

    except WebSocketDisconnect:
        pass
    finally:
        if master_fd >= 0:
            with contextlib.suppress(OSError):
                os.close(master_fd)
        if proc and proc.returncode is None:
            proc.terminate()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(proc.wait(), timeout=2.0)
        db.close()
