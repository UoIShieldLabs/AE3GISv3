import re
import uuid
import ipaddress

import yaml

IP_RE = re.compile(r'ip addr (?:add|replace) (\d+\.\d+\.\d+\.\d+)/(\d+)')

_SITE_POSITIONS = [
    (100, 100), (450, 100), (800, 100),
    (100, 400), (450, 400), (800, 400),
]


def _infer_type(image: str, exec_cmds: list[str]) -> str:
    joined = ' '.join(exec_cmds)
    if 'frr' in image and 'ip_forward' in joined:
        return 'router'
    if 'br0 type bridge' in joined or 'ip link add br0' in joined:
        return 'switch'
    return 'workstation'


def _extract_ip(exec_cmds: list[str]) -> tuple[str, str] | None:
    """Returns (ip, prefix_len) or None."""
    for cmd in exec_cmds:
        m = IP_RE.search(cmd)
        if m:
            return m.group(1), m.group(2)
    return None


def parse_clab(yaml_content: str) -> dict:
    data = yaml.safe_load(yaml_content)
    nodes_raw = data.get('topology', {}).get('nodes', {}) or {}
    links_raw = data.get('topology', {}).get('links', []) or []

    # Build container records keyed by node name
    containers: dict[str, dict] = {}
    for node_name, cfg in nodes_raw.items():
        cfg = cfg or {}
        exec_cmds = cfg.get('exec', []) or []
        image = cfg.get('image', 'alpine:latest')
        ctype = _infer_type(image, exec_cmds)
        ip_info = _extract_ip(exec_cmds)
        group = cfg.get('group') or None  # used as site grouping
        containers[node_name] = {
            'id': str(uuid.uuid4()).replace('-', ''),
            'name': node_name,
            'type': ctype,
            'ip': ip_info[0] if ip_info else '',
            'prefix': ip_info[1] if ip_info else '24',
            'image': image if image not in ('alpine:latest', 'frrouting/frr:latest') else None,
            'group': group,
        }

    # Determine if any nodes carry a group label (multi-site mode)
    has_groups = any(c['group'] for c in containers.values())

    # Group containers into site_group -> cidr -> [container] buckets
    site_cidr_map: dict[str, dict[str, list]] = {}
    no_ip: list = []
    for node_name, c in containers.items():
        site_key = c['group'] if has_groups and c['group'] else 'Imported Site'
        if c['ip']:
            try:
                net = ipaddress.IPv4Interface(f"{c['ip']}/{c['prefix']}").network
                cidr = str(net)
                site_cidr_map.setdefault(site_key, {}).setdefault(cidr, []).append(c)
            except ValueError:
                no_ip.append(c)
        else:
            no_ip.append(c)

    # Put no-IP nodes in a catch-all bucket
    if no_ip:
        site_cidr_map.setdefault('Imported Site', {}).setdefault('0.0.0.0/0', []).extend(no_ip)

    # Build links: list of (node_name_a, node_name_b)
    link_pairs: list[tuple[str, str]] = []
    for link in links_raw:
        eps = link.get('endpoints', [])
        if len(eps) == 2:
            a = eps[0].split(':')[0]
            b = eps[1].split(':')[0]
            link_pairs.append((a, b))

    name_to_id = {name: c['id'] for name, c in containers.items()}

    # Build sites
    sites = []
    for site_idx, (site_name, cidr_map) in enumerate(site_cidr_map.items()):
        site_id = str(uuid.uuid4()).replace('-', '')
        pos_x, pos_y = (
            _SITE_POSITIONS[site_idx]
            if site_idx < len(_SITE_POSITIONS)
            else (100 + site_idx * 350, 100)
        )

        subnets = []
        for cidr, members in cidr_map.items():
            subnet_id = str(uuid.uuid4()).replace('-', '')
            gateway_ip = next(
                (c['ip'] for c in members if c['type'] == 'router' and c['ip']),
                members[0]['ip'] if members else '',
            )
            member_ids = {c['id'] for c in members}
            connections = []
            for a_name, b_name in link_pairs:
                a_id = name_to_id.get(a_name)
                b_id = name_to_id.get(b_name)
                if a_id in member_ids and b_id in member_ids:
                    connections.append({'from': a_id, 'to': b_id})

            subnet_containers = [
                {k: v for k, v in c.items() if k not in ('prefix', 'group')}
                for c in members
            ]

            subnets.append({
                'id': subnet_id,
                'name': f'Subnet {cidr}',
                'cidr': cidr if cidr != '0.0.0.0/0' else '10.0.0.0/24',
                'gateway': gateway_ip or None,
                'containers': subnet_containers,
                'connections': connections,
            })

        sites.append({
            'id': site_id,
            'name': site_name,
            'location': site_name,
            'position': {'x': pos_x, 'y': pos_y},
            'subnets': subnets,
            'subnetConnections': [],
        })

    return {
        'sites': sites,
        'siteConnections': [],
    }
