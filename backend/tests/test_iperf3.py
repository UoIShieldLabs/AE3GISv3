"""iperf3 command lines, the json-stream parser (on real output) and summaries."""

from pathlib import Path

import pytest

from domain.traffic.iperf3 import Iperf3StreamParser, client_argv, is_interrupt, server_argv
from domain.traffic.summary import summarize_flow

FIX = Path(__file__).parent / "fixtures" / "iperf3"


def _parse(name: str, role: str, chunk: int = 97):
    data = (FIX / f"{name}_{role}.ndjson").read_bytes()
    p = Iperf3StreamParser("f1", role, offset=10.0)
    events = []
    for i in range(0, len(data), chunk):  # split lines anywhere
        events += p.feed(data[i : i + chunk])
    return p, events


def _samples(events):
    return [s.to_dict() for e in events for s in e.samples]


def test_argv():
    tcp = client_argv({"protocol": "tcp", "parallel": 2, "duration_s": 30}, "10.0.2.5", 5202, 1.0)
    assert tcp[:9] == ["iperf3", "-c", "10.0.2.5", "-p", "5202", "--json-stream", "-i", "1", "-t"]
    assert tcp[9] == "30" and "-P" in tcp and "-u" not in tcp
    udp = client_argv(
        {"protocol": "udp", "bitrate": "50M", "length": 1200, "direction": "bidir"}, "h", 5201, 0.5
    )
    assert udp[udp.index("-t") + 1] == "0"  # no duration: until stopped
    assert ["-u", "-b", "50M"] == udp[udp.index("-u") : udp.index("-u") + 3]
    assert "--bidir" in udp and udp[udp.index("-i") + 1] == "0.5" and "-l" in udp
    assert "-R" in client_argv({"direction": "reverse"}, "h", 1, 1)
    assert server_argv(5201, 1) == ["iperf3", "-s", "-1", "-p", "5201", "--json-stream", "-i", "1"]


def test_tcp_forward_client_and_server():
    client, events = _parse("tcp_p2", "client")
    assert [e.kind for e in events] == ["start", "interval", "interval", "interval", "end"]
    samples = _samples(events)
    assert {(s["direction"], s["side"]) for s in samples} == {("fwd", "sender")}
    assert samples[0]["t"] == pytest.approx(11.0, abs=0.01)
    assert samples[0]["retransmits"] == 0 and samples[0]["rtt_ms"] > 0
    server, sevents = _parse("tcp_p2", "server")
    ss = _samples(sevents)
    assert {(s["direction"], s["side"]) for s in ss} == {("fwd", "receiver")}
    summary = summarize_flow(samples + ss)
    assert set(summary) == {"fwd"} and summary["fwd"]["measured_by"] == "receiver"
    assert summary["fwd"]["bps"]["mean"] > 0 and summary["fwd"]["retransmits"] == 0


def test_reverse_is_server_to_client():
    _, ce = _parse("reverse", "client")
    _, se = _parse("reverse", "server")
    both = _samples(ce) + _samples(se)
    assert {(s["direction"], s["side"]) for s in both} == {("rev", "receiver"), ("rev", "sender")}
    assert set(summarize_flow(both)) == {"rev"}


def test_bidir_has_both_directions():
    _, ce = _parse("bidir", "client")
    kinds = {(s["direction"], s["side"]) for s in _samples(ce)}
    assert kinds == {("fwd", "sender"), ("rev", "receiver")}
    _, se = _parse("bidir", "server")
    summary = summarize_flow(_samples(ce) + _samples(se))
    assert set(summary) == {"fwd", "rev"}
    assert summary["fwd"]["measured_by"] == summary["rev"]["measured_by"] == "receiver"


def test_udp_jitter_and_loss_come_from_the_server():
    _, ce = _parse("udp", "client")
    _, se = _parse("udp", "server")
    rx = [s for s in _samples(se) if s["side"] == "receiver"]
    assert rx and all("jitter_ms" in s and "lost_percent" in s for s in rx)
    fwd = summarize_flow(_samples(ce) + _samples(se))["fwd"]
    assert fwd["lost_packets"] == 0 and fwd["lost_percent"] == 0 and fwd["packets"] > 0
    assert fwd["jitter_ms"]["max"] >= fwd["jitter_ms"]["min"]


def test_interrupted_runs_report_errors_the_runner_ignores():
    client, events = _parse("tcp_until_stopped", "client")
    assert [e.kind for e in events][-2:] == ["error", "end"]
    assert client.errors and is_interrupt(client.errors[0])
    assert client.end["sum_received"]["bits_per_second"] == 0  # the client never hears back
    server, _ = _parse("tcp_until_stopped", "server")
    assert is_interrupt(server.errors[0])
    assert not is_interrupt("unable to connect to server - server may have stopped running")


def test_garbage_lines_are_skipped():
    p = Iperf3StreamParser("f", "client")
    assert p.feed(b'not json\n[1,2]\n{"event": "weird"}\n')[0].kind == "other"
