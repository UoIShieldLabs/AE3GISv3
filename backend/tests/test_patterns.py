"""Traffic patterns → flows, ports and offered rates."""

import pytest

from domain.traffic.patterns import (
    PatternError,
    assign_ports,
    bitrate_bps,
    expand,
    offered_bps,
)

NODES = ["a", "b", "c", "d"]


def pick(selector):
    if selector in (None, "all") or selector == {"roles": ["host"]}:
        return NODES
    return [n for n in NODES if n in selector]


def test_mesh_is_balanced():
    flows = expand([{"id": "m", "kind": "mesh", "fanout": 2, "bitrate": "5M"}], pick)
    assert len(flows) == 8
    out = {n: sum(f["client"] == n for f in flows) for n in NODES}
    into = {n: sum(f["server"] == n for f in flows) for n in NODES}
    assert set(out.values()) == set(into.values()) == {2}
    assert flows[0] == {"id": "m.1", "client": "a", "server": "b", "pattern": "m", "bitrate": "5M"}
    full = expand([{"id": "m", "kind": "mesh", "fanout": 99}], pick)
    assert len(full) == 12  # fanout is capped at n - 1: a full mesh


def test_clients_to_servers():
    one = expand([{"id": "p", "kind": "clients_to_servers", "servers": ["c", "d"]}], pick)
    assert [(f["client"], f["server"]) for f in one] == [("a", "c"), ("b", "d")]
    every = expand(
        [
            {
                "id": "p",
                "kind": "clients_to_servers",
                "servers": ["d"],
                "clients": ["a", "b", "d"],
                "each": "all",
            }
        ],
        pick,
    )
    assert [(f["client"], f["server"]) for f in every] == [("a", "d"), ("b", "d")]
    with pytest.raises(PatternError) as exc:
        expand([{"id": "p", "kind": "clients_to_servers", "servers": ["zz"]}], pick)
    assert exc.value.code == "no_servers"
    with pytest.raises(PatternError) as exc:
        expand([{"id": "p", "kind": "clients_to_servers", "servers": NODES}], pick)
    assert exc.value.code == "no_clients"


def test_zero_bitrate_means_unlimited_and_ports_count_per_server():
    flows = expand([{"id": "m", "kind": "mesh", "fanout": 3, "bitrate": "0", "parallel": 2}], pick)
    assert "bitrate" not in flows[0] and flows[0]["parallel"] == 2
    assign_ports(flows)
    by_server = {}
    for f in flows:
        by_server.setdefault(f["server"], []).append(f["port"])
    assert all(ports == [5201, 5202, 5203] for ports in by_server.values())


def test_offered_rates():
    assert bitrate_bps("10M") == 10e6 and bitrate_bps("1.5G") == 1.5e9 and bitrate_bps("800") == 800
    assert bitrate_bps(None) is None and bitrate_bps("fast") is None
    assert offered_bps({"bitrate": "10M", "parallel": 2, "direction": "bidir"}) == 40e6
    assert offered_bps({"protocol": "tcp"}) is None  # as fast as it goes
    assert offered_bps({"protocol": "udp"}) == 1e6  # iperf3's UDP default
