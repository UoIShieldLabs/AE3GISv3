"""Stats samples → rates."""

from domain.telemetry import rates
from engine.base import IfaceCounters, RawStats


def _raw(ts, cpu, sysc, rx, tx, **kw):
    return RawStats(
        target="rA",
        kind="node",
        ts=ts,
        cpu_total_ns=cpu,
        system_cpu_ns=sysc,
        online_cpus=8,
        mem_usage=50_000_000,
        mem_inactive_file=10_000_000,
        mem_limit=8_000_000_000,
        pids=4,
        ifaces={
            "eth0": IfaceCounters(
                rx_bytes=rx, tx_bytes=tx, rx_packets=rx // 100, tx_packets=tx // 100
            )
        },
        **kw,
    )


def test_first_sample_has_no_rates():
    s = rates(None, _raw(1.0, 0, 0, 0, 0), 0.0)
    assert s["cpu_percent"] is None and s["ifaces"] == {} and s["mem_used"] == 40_000_000


def test_cpu_and_interface_rates():
    a = _raw(10.0, 1_000_000_000, 80_000_000_000, 0, 0)
    b = _raw(11.0, 1_500_000_000, 88_000_000_000, 1_250_000, 250_000)
    s = rates(a, b, 1.0)
    assert s["cpu_percent"] == 50.0  # half a core
    assert s["ifaces"]["eth0"]["rx_bps"] == 10_000_000 and s["ifaces"]["eth0"]["rx_pps"] == 12500
    # Without system CPU (some hosts), CPU falls back to wall time.
    c = _raw(12.0, 2_000_000_000, None, 1_250_000, 250_000)
    assert rates(b, c, 2.0)["cpu_percent"] == 50.0


def test_counter_resets_are_skipped():
    a = _raw(1.0, 0, 0, 5_000, 5_000)
    b = _raw(2.0, 0, 0, 10, 10)
    assert rates(a, b, 1.0)["ifaces"] == {}
