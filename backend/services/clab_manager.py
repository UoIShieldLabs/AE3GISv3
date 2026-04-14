"""Manage ContainerLab lifecycle: deploy, destroy, inspect."""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
import shutil
from pathlib import Path

from config import CLAB_WORKDIR
from services import clab_generator

log = logging.getLogger(__name__)
_FW_CHAIN = "AE3GIS-FW"
_PERSIST_ROOT = CLAB_WORKDIR / "persistent"
_PERSIST_META_ROOT = CLAB_WORKDIR / "persistent-meta"


def _yaml_path(topology_id: str) -> Path:
    return CLAB_WORKDIR / f"{topology_id}.clab.yml"


def deployment_name(topology_id: str, topology_data: dict | None = None) -> str:
    """Return a deterministic, unique containerlab topology name per record."""
    import re
    base = (topology_data or {}).get("name") or "ae3gis-topology"
    base = str(base).strip() or "ae3gis-topology"
    # ContainerLab node names must contain only alphanumerics, hyphens, underscores
    base = re.sub(r"[^a-zA-Z0-9_-]", "-", base)
    base = re.sub(r"-{2,}", "-", base).strip("-") or "ae3gis-topology"
    return f"{base}-{topology_id[:8]}"


def management_network_name(topology_id: str) -> str:
    """Return a deterministic management network name per topology."""
    return f"ae3gis-mgmt-{topology_id[:8]}"


def _mgmt_seed(topology_id: str) -> int:
    # Use up to 32 bits of topology id for better spread.
    return int(topology_id[:8], 16)


def management_ipv4_subnet(topology_id: str, attempt: int = 0) -> str:
    """Return a deterministic management IPv4 subnet per topology.

    Uses 100.64.0.0/10 with /24s. This avoids Docker's default bridge
    network (172.17.0.0/16), which was causing frequent overlaps.
    """
    # 100.64.0.0/10 -> second octet 64..127 and third octet 0..255
    total_slots = 64 * 256
    slot = (_mgmt_seed(topology_id) + (attempt * 9973)) % total_slots
    second_octet = 64 + (slot // 256)  # 64..127
    third_octet = slot % 256
    return f"100.{second_octet}.{third_octet}.0/24"


def management_ipv6_subnet(topology_id: str, attempt: int = 0) -> str:
    """Return a deterministic management IPv6 subnet per topology (/64)."""
    total_slots = 64 * 256
    slot = (_mgmt_seed(topology_id) + (attempt * 9973)) % total_slots
    second_octet = 64 + (slot // 256)
    third_octet = slot % 256
    return f"3fff:100:{second_octet}:{third_octet}::/64"


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


async def _docker_exec(
    docker_name: str,
    args: list[str],
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    env_flags: list[str] = []
    for k, v in (env or {}).items():
        env_flags += ["-e", f"{k}={v}"]
    return await _run(["sudo", "docker", "exec", *env_flags, docker_name, *args])


def build_topology_env(topology_data: dict, target_container_id: str = "") -> dict[str, str]:
    """Build env vars describing the topology for script consumption.

    Provides:
      TOPO_NAME                          — topology name
      TARGET_ID, TARGET_IP, TARGET_TYPE  — the container the script runs on
      CONTAINER_{NAME}_IP               — IP for every container (name uppercased, hyphens → underscores)
      CONTAINER_{NAME}_TYPE             — type for every container
      SUBNET_{NAME}_CIDR                — CIDR for every subnet
      SUBNET_{NAME}_GATEWAY             — gateway for every subnet
      SITE_{NAME}                        — site name
    """
    env: dict[str, str] = {}
    env["TOPO_NAME"] = topology_data.get("name") or ""

    for site in topology_data.get("sites", []):
        site_key = _env_key(site.get("name", ""))
        if site_key:
            env[f"SITE_{site_key}"] = site.get("name", "")
        for subnet in site.get("subnets", []):
            sn_key = _env_key(subnet.get("name", ""))
            if sn_key:
                env[f"SUBNET_{sn_key}_CIDR"] = subnet.get("cidr", "")
                env[f"SUBNET_{sn_key}_GATEWAY"] = subnet.get("gateway", "")
            for c in subnet.get("containers", []):
                c_key = _env_key(c.get("name", ""))
                if c_key:
                    env[f"CONTAINER_{c_key}_IP"] = c.get("ip", "")
                    env[f"CONTAINER_{c_key}_TYPE"] = c.get("type", "")
                    env[f"CONTAINER_{c_key}_ID"] = c.get("id", "")
                if c.get("id") == target_container_id:
                    env["TARGET_ID"] = c.get("id", "")
                    env["TARGET_IP"] = c.get("ip", "")
                    env["TARGET_TYPE"] = c.get("type", "")
                    env["TARGET_NAME"] = c.get("name", "")
                    env["TARGET_SUBNET"] = subnet.get("name", "")
                    env["TARGET_SUBNET_CIDR"] = subnet.get("cidr", "")
                    env["TARGET_GATEWAY"] = subnet.get("gateway", "")

    return env


def _env_key(name: str) -> str:
    """Sanitize a name into a valid env var component (uppercase, underscores)."""
    return name.upper().replace(" ", "_").replace("-", "_").replace(".", "_")


def _iter_containers(topology_data: dict) -> list[dict]:
    containers: list[dict] = []
    for site in topology_data.get("sites", []):
        for subnet in site.get("subnets", []):
            containers.extend(subnet.get("containers", []))
    return containers


async def _remove_fs_path(path: Path) -> None:
    if not path.exists():
        return
    cmd = ["sudo", "rm", "-rf", "--", str(path)] if path.is_dir() else ["sudo", "rm", "-f", "--", str(path)]
    rc, _stdout, stderr = await _run(cmd)
    if rc != 0:
        raise RuntimeError(f"failed to remove path {path}: {stderr.strip()}")


async def prune_removed_persistence_paths(topology_id: str, topology_data: dict) -> None:
    """Delete backend persistence dirs/sentinels no longer present in topology data."""
    desired: dict[str, set[str]] = {}
    for container in _iter_containers(topology_data):
        container_id = (container.get("id") or "").strip()
        if not container_id:
            continue
        keep: set[str] = set()
        for raw_path in container.get("persistencePaths", []) or []:
            container_path = clab_generator.normalize_persistence_path(str(raw_path))
            if not container_path:
                continue
            host_path = clab_generator.persistence_host_path(topology_id, container_id, container_path)
            keep.add(host_path.name)
        desired[container_id] = keep

    persist_topology_root = _PERSIST_ROOT / topology_id
    meta_topology_root = _PERSIST_META_ROOT / topology_id

    if persist_topology_root.exists():
        for container_dir in persist_topology_root.iterdir():
            if not container_dir.is_dir():
                continue
            container_id = container_dir.name
            keep = desired.get(container_id, set())
            sentinel_dir = meta_topology_root / container_id
            for host_dir in container_dir.iterdir():
                if host_dir.name in keep:
                    continue
                await _remove_fs_path(host_dir)
                await _remove_fs_path(sentinel_dir / f"{host_dir.name}.seeded")
                log.info(
                    "Removed stale persistence path for %s/%s (%s)",
                    topology_id,
                    container_id,
                    host_dir.name,
                )
            if not any(container_dir.iterdir()):
                await _remove_fs_path(container_dir)
            if sentinel_dir.exists() and not any(sentinel_dir.iterdir()):
                await _remove_fs_path(sentinel_dir)

    if meta_topology_root.exists():
        for sentinel_dir in meta_topology_root.iterdir():
            if not sentinel_dir.is_dir():
                continue
            container_id = sentinel_dir.name
            keep = desired.get(container_id, set())
            for sentinel in sentinel_dir.iterdir():
                digest = sentinel.name[:-7] if sentinel.name.endswith(".seeded") else sentinel.name
                if digest in keep:
                    continue
                await _remove_fs_path(sentinel)
            if not any(sentinel_dir.iterdir()):
                await _remove_fs_path(sentinel_dir)

        if not any(meta_topology_root.iterdir()):
            await _remove_fs_path(meta_topology_root)

    if persist_topology_root.exists() and not any(persist_topology_root.iterdir()):
        await _remove_fs_path(persist_topology_root)


async def _seed_persistence_from_image(image: str, container_path: str, host_path: Path) -> None:
    """Populate host_path with initial contents from image:container_path."""
    src = shlex.quote(container_path)
    seed_cmd = (
        f"if [ -d {src} ]; then "
        f"cp -a {src}/. /ae3gis-seed/; "
        f"elif [ -e {src} ]; then "
        f"cp -a {src} /ae3gis-seed/; "
        "else "
        "exit 42; "
        "fi"
    )
    rc, _stdout, stderr = await _run([
        "sudo",
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "sh",
        "-v",
        f"{host_path}:/ae3gis-seed",
        image,
        "-lc",
        seed_cmd,
    ])
    if rc == 42:
        log.warning("Seed source path %s does not exist in image %s; leaving %s empty", container_path, image, host_path)
        return
    if rc != 0:
        raise RuntimeError(f"failed to seed {container_path} from {image}: {stderr.strip()}")


async def prepare_persistence_paths(topology_id: str, topology_data: dict) -> None:
    """Ensure persistent bind paths exist and are initialized once from image defaults."""
    await prune_removed_persistence_paths(topology_id, topology_data)

    for container in _iter_containers(topology_data):
        container_id = (container.get("id") or "").strip()
        if not container_id:
            continue

        container_type = (container.get("type") or "").strip()
        image = clab_generator.resolve_container_image(container, container_type)
        raw_paths = container.get("persistencePaths", []) or []
        for raw_path in raw_paths:
            container_path = clab_generator.normalize_persistence_path(str(raw_path))
            if not container_path:
                continue
            host_path = clab_generator.persistence_host_path(topology_id, container_id, container_path)
            host_path.mkdir(parents=True, exist_ok=True)

            sentinel_dir = _PERSIST_META_ROOT / topology_id / container_id
            sentinel_dir.mkdir(parents=True, exist_ok=True)
            sentinel = sentinel_dir / f"{host_path.name}.seeded"
            if sentinel.exists():
                continue

            # If this path is being seeded as "new", clear any stale contents
            # so re-adding persistence always starts from a vanilla image path.
            for child in host_path.iterdir():
                await _remove_fs_path(child)

            await _seed_persistence_from_image(image, container_path, host_path)
            sentinel.write_text("seeded\n")


async def _detect_iptables_bin(docker_name: str) -> str:
    rc, stdout, stderr = await _docker_exec(
        docker_name,
        ["sh", "-lc", "command -v iptables >/dev/null 2>&1 && echo iptables || (command -v iptables-nft >/dev/null 2>&1 && echo iptables-nft)"],
    )
    if rc != 0:
        raise RuntimeError(f"failed to detect iptables binary: {stderr.strip()}")
    ipt = stdout.strip()
    if ipt not in {"iptables", "iptables-nft"}:
        raise RuntimeError("iptables not found in container")
    return ipt


def _docker_name(topology_name: str, container_id: str) -> str:
    return f"clab-{topology_name}-{container_id}"


def _parse_chain_rules(output: str) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith(f"-A {_FW_CHAIN} "):
            continue
        parts = line.split()
        rule = {
            "source": "any",
            "destination": "any",
            "protocol": "any",
            "port": "-",
            "action": "accept",
        }
        i = 0
        while i < len(parts):
            tok = parts[i]
            nxt = parts[i + 1] if i + 1 < len(parts) else ""
            if tok == "-s" and nxt:
                rule["source"] = nxt
                i += 2
                continue
            if tok == "-d" and nxt:
                rule["destination"] = nxt
                i += 2
                continue
            if tok == "-p" and nxt:
                rule["protocol"] = nxt.lower()
                i += 2
                continue
            if tok == "--dport" and nxt:
                rule["port"] = nxt
                i += 2
                continue
            if tok == "-j" and nxt:
                rule["action"] = nxt.lower()
                i += 2
                continue
            i += 1

        if rule["protocol"] not in {"any", "tcp", "udp", "icmp"}:
            rule["protocol"] = "any"
        if rule["action"] not in {"accept", "drop"}:
            rule["action"] = "accept"
        if rule["protocol"] in {"any", "icmp"}:
            rule["port"] = "-"
        rules.append(rule)
    return rules


async def pull_images(topology_data: dict) -> None:
    """Pre-pull all unique container images so deploy doesn't fail on missing images.

    Also pulls the Wireshark capture image so that opening a capture session
    doesn't stall on a first-time image download.
    """
    from services.capture_manager import CAPTURE_IMAGE

    images: set[str] = set()
    for container in _iter_containers(topology_data):
        image = clab_generator.resolve_container_image(container, container.get("type", ""))
        images.add(image)

    # Always ensure the Wireshark sidecar image is local
    images.add(CAPTURE_IMAGE)

    for image in images:
        # Skip pull if image is already present locally
        rc_check, _, _ = await _run(["sudo", "docker", "image", "inspect", image])
        if rc_check == 0:
            log.info("Image already local, skipping pull: %s", image)
            continue
        log.info("Pulling image: %s", image)
        rc, stdout, stderr = await _run(["sudo", "docker", "pull", image])
        if rc != 0:
            log.error("Failed to pull image %s: %s", image, stderr.strip())
            # Only hard-fail for topology images; Wireshark is optional
            if image != CAPTURE_IMAGE:
                raise RuntimeError(f"Failed to pull image '{image}': {stderr.strip()}")
            log.warning("Wireshark image pull failed — capture may be slow on first use")
        else:
            log.info("Pulled image: %s", image)


async def deploy(topology_id: str) -> str:
    """Deploy a topology. Returns containerlab stdout."""
    path = _yaml_path(topology_id)
    if not path.exists():
        raise FileNotFoundError(f"YAML not found: {path}")

    mgmt_net = management_network_name(topology_id)
    last_stderr = ""

    for attempt in range(4):
        ipv4_subnet = management_ipv4_subnet(topology_id, attempt)
        ipv6_subnet = management_ipv6_subnet(topology_id, attempt)
        deploy_cmd = [
            "sudo", "containerlab", "deploy",
            "-t", str(path),
            "--network", mgmt_net,
            "--ipv4-subnet", ipv4_subnet,
            "--ipv6-subnet", ipv6_subnet,
            "--reconfigure",
        ]

        rc, stdout, stderr = await _run(deploy_cmd)
        log.info("containerlab deploy stdout:\n%s", stdout)
        if rc == 0:
            return stdout

        last_stderr = stderr
        overlap_error = "overlap" in stderr.lower() and "subnet" in stderr.lower()
        stale_bridge_error = "Failed to lookup link \"br-" in stderr and "Link not found" in stderr

        # Self-heal stale docker network metadata that references a missing
        # bridge device (e.g., `Failed to lookup link "br-xxxx": Link not found`).
        if stale_bridge_error:
            log.warning(
                "Detected stale docker bridge state for management network %s. "
                "Removing network and retrying deploy.",
                mgmt_net,
            )
            rm_rc, rm_stdout, rm_stderr = await _run(["sudo", "docker", "network", "rm", mgmt_net])
            log.info("docker network rm stdout:\n%s", rm_stdout)
            if rm_rc != 0:
                log.warning("docker network rm stderr:\n%s", rm_stderr)
            continue

        if overlap_error and attempt < 3:
            log.warning(
                "Management subnet overlap for topology %s using %s/%s. "
                "Retrying with a different deterministic subnet.",
                topology_id,
                ipv4_subnet,
                ipv6_subnet,
            )
            continue

        break

    log.error("containerlab deploy stderr:\n%s", last_stderr)
    raise RuntimeError(f"containerlab deploy failed:\n{last_stderr}")


async def get_firewall_rules(topology_name: str, container_id: str) -> list[dict[str, str]]:
    """Read managed firewall rules from the AE3GIS chain inside a container."""
    docker_name = _docker_name(topology_name, container_id)
    ipt = await _detect_iptables_bin(docker_name)

    rc, stdout, stderr = await _docker_exec(docker_name, [ipt, "-S", _FW_CHAIN])
    if rc != 0:
        err = stderr.lower()
        if "no chain/target/match" in err:
            return []
        raise RuntimeError(stderr.strip() or "failed to read firewall rules")
    return _parse_chain_rules(stdout)


async def apply_firewall_rules(
    topology_name: str,
    container_id: str,
    rules: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Replace managed firewall rules in AE3GIS chain inside a container."""
    docker_name = _docker_name(topology_name, container_id)
    ipt = await _detect_iptables_bin(docker_name)

    # Ensure chain exists.
    await _docker_exec(docker_name, ["sh", "-lc", f"{ipt} -N {_FW_CHAIN} 2>/dev/null || true"])
    # Ensure FORWARD jumps to our chain (top priority).
    await _docker_exec(
        docker_name,
        ["sh", "-lc", f"{ipt} -C FORWARD -j {_FW_CHAIN} >/dev/null 2>&1 || {ipt} -I FORWARD 1 -j {_FW_CHAIN}"],
    )
    # Clear existing managed rules.
    rc, _stdout, stderr = await _docker_exec(docker_name, [ipt, "-F", _FW_CHAIN])
    if rc != 0:
        raise RuntimeError(stderr.strip() or "failed to flush firewall chain")

    for rule in rules:
        args = [ipt, "-A", _FW_CHAIN]
        source = (rule.get("source") or "").strip()
        destination = (rule.get("destination") or "").strip()
        protocol = (rule.get("protocol") or "any").strip().lower()
        port = (rule.get("port") or "-").strip()
        action = (rule.get("action") or "accept").strip().upper()

        if source and source.lower() != "any":
            args += ["-s", source]
        if destination and destination.lower() != "any":
            args += ["-d", destination]
        if protocol != "any":
            args += ["-p", protocol]
        if protocol in {"tcp", "udp"} and port and port != "-":
            args += ["--dport", port]
        args += ["-j", action]

        rc, _stdout, stderr = await _docker_exec(docker_name, args)
        if rc != 0:
            raise RuntimeError(stderr.strip() or "failed to apply firewall rule")

    return await get_firewall_rules(topology_name, container_id)


async def _force_destroy_containers(topology_id: str) -> str:
    """Fallback: remove containers by Docker label + remove management network.

    Used when `containerlab destroy` itself fails (e.g. subnet overlap prevents
    ContainerLab from recreating the management network during tear-down).
    """
    path = _yaml_path(topology_id)
    log.warning(
        "containerlab destroy failed for %s — falling back to manual Docker cleanup",
        topology_id,
    )

    # Find containers that belong to this lab via the topo-file label.
    rc, ids_out, _ = await _run([
        "sudo", "docker", "ps", "-a", "-q",
        "--filter", f"label=clab-topo-file={path}",
    ])
    container_ids = ids_out.strip().split() if ids_out.strip() else []

    removed: list[str] = []
    if container_ids:
        rm_rc, _, rm_err = await _run(["sudo", "docker", "rm", "-f"] + container_ids)
        if rm_rc == 0:
            removed = container_ids
            log.info("Forcibly removed %d containers for topology %s", len(removed), topology_id)
        else:
            log.warning("docker rm -f failed: %s", rm_err.strip())

    # Remove management network.
    mgmt_net = management_network_name(topology_id)
    await _run(["sudo", "docker", "network", "rm", mgmt_net])

    if not container_ids:
        return f"Force cleanup: no containers found (label=clab-topo-file={path})"
    return f"Force cleanup: removed {len(removed)} container(s) for topology {topology_id}"


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
        # ContainerLab's destroy internally tries to recreate the management
        # network, which can fail with a subnet-overlap error when another
        # Docker network (e.g. a stale compose project) occupies the same
        # range.  In that case fall back to manual container + network removal.
        if "overlap" in stderr.lower() or "pool overlaps" in stderr.lower():
            return await _force_destroy_containers(topology_id)
        raise RuntimeError(f"containerlab destroy failed:\n{stderr}")

    # Remove the management Docker network so it doesn't linger.
    mgmt_net = management_network_name(topology_id)
    rm_rc, _, rm_stderr = await _run(["sudo", "docker", "network", "rm", mgmt_net])
    if rm_rc != 0:
        log.warning("Could not remove management network %s: %s", mgmt_net, rm_stderr.strip())
    else:
        log.info("Removed management network %s", mgmt_net)

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

    Uses docker ps directly (more reliable than containerlab inspect).
    Falls back to an empty list on failure.
    """
    prefix = f"clab-{topology_name}-"
    rc, stdout, stderr = await _run([
        "sudo", "docker", "ps", "-a",
        "--filter", f"name={prefix}",
        "--format", "{{.Names}}\t{{.State}}",
    ])
    if rc != 0:
        log.warning("docker ps failed: %s", stderr)
        return []

    containers = []
    for line in stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        name, state = parts
        containers.append({"name": name.strip(), "state": state.strip()})
    return containers
