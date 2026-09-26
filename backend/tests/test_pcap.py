"""pcap stream framing and packet summaries (domain/pcap.py, domain/packets.py)."""

import struct
from pathlib import Path

import pytest

from domain.packets import summarize
from domain.pcap import PcapError, PcapSplitter, global_header, record

FIXTURE = Path(__file__).parent / "fixtures" / "pcap" / "icmp-ping.pcap"


def _eth(ethertype: int, payload: bytes, src=b"\x02" * 6, dst=b"\x04" * 6) -> bytes:
    return dst + src + struct.pack("!H", ethertype) + payload


def _ipv4(proto: int, payload: bytes, src="10.0.1.5", dst="10.0.2.5", frag=0) -> bytes:
    import ipaddress

    total = 20 + len(payload)
    hdr = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        total,
        1,
        frag,
        64,
        proto,
        0,
        ipaddress.IPv4Address(src).packed,
        ipaddress.IPv4Address(dst).packed,
    )
    return hdr + payload


def _tcp(sport, dport, flags, payload=b""):
    return struct.pack("!HHIIHHHH", sport, dport, 100, 7, (5 << 12) | flags, 512, 0, 0) + payload


def test_real_capture_splits_into_whole_records_in_any_chunking():
    data = FIXTURE.read_bytes()
    whole = PcapSplitter().feed(data)
    assert len(whole) == 10
    for size in (1, 7, 23, 24, 25, 100):
        sp = PcapSplitter()
        recs = []
        for i in range(0, len(data), size):
            recs += sp.feed(data[i : i + size])
        assert [r.raw for r in recs] == [r.raw for r in whole] and sp.pending == 0
    assert sp.linktype == 1 and sp.header == data[:24]


def test_real_capture_summaries():
    sp = PcapSplitter()
    recs = sp.feed(FIXTURE.read_bytes())
    s = [summarize(i + 1, r.ts, r.data, r.origlen, sp.linktype) for i, r in enumerate(recs)]
    assert (s[0].src, s[0].dst, s[0].proto) == ("10.0.1.5", "10.0.2.5", "ICMP")
    assert s[0].info.startswith("Echo request id=") and s[0].info.endswith("seq=1")
    assert s[1].info.startswith("Echo reply") and s[1].src == "10.0.2.5"
    assert s[0].len == 98


def test_written_records_round_trip_and_nanosecond_big_endian_headers_parse():
    frame = _eth(0x0800, _ipv4(17, struct.pack("!HHHH", 5000, 53, 12, 0) + b"abcd"))
    stream = global_header() + record(1.5, frame) + record(2.25, frame)
    recs = PcapSplitter().feed(stream)
    assert [r.ts for r in recs] == [1.5, 2.25] and recs[0].data == frame

    be = struct.pack(">IHHiIII", 0xA1B23C4D, 2, 4, 0, 0, 65535, 1)
    be += struct.pack(">IIII", 3, 500_000_000, len(frame), len(frame)) + frame
    sp = PcapSplitter()
    [r] = sp.feed(be)
    assert r.ts == 3.5 and sp.snaplen == 65535


def test_garbage_and_corrupt_records_raise():
    with pytest.raises(PcapError):
        PcapSplitter().feed(b"not a pcap stream at all")
    bad = global_header() + struct.pack("<IIII", 0, 0, 10_000_000, 10)
    with pytest.raises(PcapError):
        PcapSplitter().feed(bad)


@pytest.mark.parametrize(
    ("frame", "proto", "info"),
    [
        (
            _eth(0x0800, _ipv4(6, _tcp(40000, 502, 0x18, b"\x00" * 12))),
            "Modbus/TCP",
            "40000 → 502 [ACK, PSH] Seq=100 Ack=7 Win=512 Len=12",
        ),
        (
            _eth(0x0800, _ipv4(6, _tcp(40000, 80, 0x02))),
            "TCP",
            "40000 → 80 [SYN] Seq=100 Win=512 Len=0",
        ),
        (
            _eth(0x0800, _ipv4(17, struct.pack("!HHHH", 5201, 40000, 108, 0) + b"x" * 100)),
            "iperf3",
            "5201 → 40000 Len=100",
        ),
        (
            _eth(0x0800, _ipv4(1, bytes([3, 1, 0, 0, 0, 0, 0, 0]))),
            "ICMP",
            "Destination unreachable (code 1)",
        ),
        (_eth(0x0800, _ipv4(6, b"", frag=0x0010)), "IPv4", "Fragment offset 128"),
        (_eth(0x0800, _ipv4(89, b"\x02" * 24)), "OSPF", "OSPF"),
        (_eth(0x88CC, b"\x00" * 10), "LLDP", "Link Layer Discovery Protocol"),
        (_eth(0x9999, b""), "0x9999", "Ethertype 0x9999"),
    ],
)
def test_summaries(frame, proto, info):
    s = summarize(1, 0.0, frame, len(frame), 1)
    assert (s.proto, s.info) == (proto, info)


def test_arp_vlan_and_ipv6():
    arp = struct.pack("!HHBBH", 1, 0x0800, 6, 4, 1) + b"\x02" * 6 + bytes([10, 0, 1, 5])
    arp += b"\x00" * 6 + bytes([10, 0, 1, 1])
    s = summarize(1, 0.0, _eth(0x0806, arp), 42, 1)
    assert (s.proto, s.src, s.dst, s.info) == (
        "ARP",
        "10.0.1.5",
        "10.0.1.1",
        "Who has 10.0.1.1? Tell 10.0.1.5",
    )
    tagged = _eth(0x8100, struct.pack("!HH", 42, 0x0806) + arp)
    assert summarize(1, 0.0, tagged, 46, 1).info.startswith("VLAN 42 · Who has")
    icmp6 = bytes([128, 0, 0, 0, 0, 1, 0, 2])
    v6 = struct.pack("!IHBB", 0x60000000, len(icmp6), 58, 64) + b"\xfe\x80" + b"\x00" * 13 + b"\x01"
    v6 += b"\xfe\x80" + b"\x00" * 13 + b"\x02" + icmp6
    s = summarize(1, 0.0, _eth(0x86DD, v6), 70, 1)
    assert (s.proto, s.src, s.info) == ("ICMPv6", "fe80::1", "Echo request id=1 seq=2")


def test_truncated_and_foreign_link_types_never_raise():
    s = summarize(1, 0.0, _eth(0x0800, b"\x45\x00"), 100, 1)
    assert s.info.endswith("[truncated]")
    assert summarize(1, 0.0, b"", 0, 1).info.endswith("[truncated]")
    assert summarize(1, 0.0, b"\x00" * 20, 20, 276).proto == "?"
