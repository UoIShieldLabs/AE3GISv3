"""Manage ContainerLab lifecycle: deploy, destroy, inspect."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path

from config import CLAB_WORKDIR

log = logging.getLogger(__name__)


def _yaml_path(topology_id: str) -> Path:
    return CLAB_WORKDIR / f"{topology_id}.clab.yml"


def write_yaml(topology_id: str, yaml_content: str) -> Path:
    """Write the clab YAML to the workdir and return the file path."""
    path = _yaml_path(topology_id)
    path.write_text(yaml_content)
    return path


async def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    log.info("Running: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


async def deploy(topology_id: str) -> str:
    """Deploy a topology. Returns containerlab stdout."""
    path = _yaml_path(topology_id)
    if not path.exists():
        raise FileNotFoundError(f"YAML not found: {path}")

    rc, stdout, stderr = await _run([
        "sudo", "containerlab", "deploy",
        "-t", str(path),
        "--reconfigure",
    ])
    log.info("containerlab deploy stdout:\n%s", stdout)
    if rc != 0:
        log.error("containerlab deploy stderr:\n%s", stderr)
        raise RuntimeError(f"containerlab deploy failed:\n{stderr}")
    return stdout


async def destroy(topology_id: str) -> str:
    """Destroy a deployed topology. Returns containerlab stdout."""
    path = _yaml_path(topology_id)
    if not path.exists():
        raise FileNotFoundError(f"YAML not found: {path}")

    rc, stdout, stderr = await _run([
        "sudo", "containerlab", "destroy",
        "-t", str(path),
    ])
    if rc != 0:
        raise RuntimeError(f"containerlab destroy failed:\n{stderr}")
    return stdout


def cleanup(topology_id: str, topology_name: str) -> None:
    """Remove the YAML file and clab working directory for a topology."""
    yaml_file = _yaml_path(topology_id)
    if yaml_file.exists():
        yaml_file.unlink()
        log.info("Removed %s", yaml_file)

    # ContainerLab creates clab-{topo_name}/ in the working directory
    clab_dir = CLAB_WORKDIR / f"clab-{topology_name}"
    if clab_dir.exists():
        shutil.rmtree(clab_dir, ignore_errors=True)
        log.info("Removed %s", clab_dir)


async def inspect(topology_name: str) -> list[dict]:
    """Inspect a running topology, return list of container statuses.

    Falls back to an empty list if containerlab is not available or the
    topology is not deployed.
    """
    rc, stdout, stderr = await _run([
        "sudo", "containerlab", "inspect",
        "--name", topology_name,
        "--format", "json",
    ])
    if rc != 0:
        log.warning("containerlab inspect failed: %s", stderr)
        return []

    try:
        data = json.loads(stdout)
        # containerlab inspect --format json returns {"containers": [...]}
        return data.get("containers", [])
    except json.JSONDecodeError:
        log.warning("Failed to parse inspect output")
        return []
