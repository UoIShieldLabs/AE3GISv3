"""What the fake engine's sidecars print: synthetic tcpdump and iperf3 output.

Shapes follow real output recorded on Docker Desktop (see
``tests/fixtures/iperf3``), so the parsers and the UI see what a real lab
produces, minus the real numbers.
"""

from __future__ import annotations

import ipaddress
import json
import struct

from domain.pcap import record


def icmp_echo_frame(src_ip: str, dst_ip: str, seq: int, reply: bool = False) -> bytes:
    """An Ethernet/IPv4/ICMP echo request (or reply) with a 56-byte payload."""
    icmp = struct.pack("!BBHHH", 0 if reply else 8, 0, 0, 0x1D, seq) + bytes(range(56))
    ip = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        20 + len(icmp),
        seq,
        0x4000,
        64,
        1,
        0,
        ipaddress.IPv4Address(src_ip).packed,
        ipaddress.IPv4Address(dst_ip).packed,
    )
    src_mac, dst_mac = b"\x02\x42\x0a\x00\x00\x01", b"\x02\x42\x0a\x00\x00\x02"
    if reply:
        src_mac, dst_mac = dst_mac, src_mac
    return dst_mac + src_mac + b"\x08\x00" + ip + icmp


def ping_records(src_ip: str, dst_ip: str, seq: int, ts: float) -> bytes:
    return record(ts, icmp_echo_frame(src_ip, dst_ip, seq)) + record(
        ts + 0.0007, icmp_echo_frame(dst_ip, src_ip, seq, reply=True)
    )


def tcpdump_banner(iface: str) -> bytes:
    return (
        f"tcpdump: listening on {iface}, link-type EN10MB (Ethernet), "
        "snapshot length 262144 bytes\n"
    ).encode()


def tcpdump_totals(captured: int) -> bytes:
    return (
        f"{captured} packets captured\n{captured} packets received by filter\n"
        "0 packets dropped by kernel\n"
    ).encode()


class IperfArgs:
    """The subset of an iperf3 command line the fake understands."""

    def __init__(self, argv: list[str]) -> None:
        self.server = "-s" in argv
        self.host = self._value(argv, "-c")
        self.port = int(self._value(argv, "-p") or 5201)
        self.duration = int(self._value(argv, "-t") or 10)
        self.udp = "-u" in argv
        self.parallel = int(self._value(argv, "-P") or 1)
        self.reverse = "-R" in argv
        self.bidir = "--bidir" in argv
        self.length = int(self._value(argv, "-l") or (1448 if not self.udp else 1460))
        self.bitrate = self._rate(self._value(argv, "-b"))

    @staticmethod
    def _value(argv: list[str], flag: str) -> str | None:
        return (
            argv[argv.index(flag) + 1]
            if flag in argv and argv.index(flag) + 1 < len(argv)
            else None
        )

    def _rate(self, raw: str | None) -> float:
        if not raw:
            return 1e6 if self.udp else 95e6
        mult = {"K": 1e3, "M": 1e6, "G": 1e9}.get(raw[-1].upper(), 1)
        return float(raw.rstrip("KMGkmg") or 0) * mult or 95e6


def _line(event: str, data) -> bytes:
    return (json.dumps({"event": event, "data": data}) + "\n").encode()


def _sum(t0: float, t1: float, bps: float, args: IperfArgs, sender: bool) -> dict:
    nbytes = int(bps * (t1 - t0) / 8)
    s = {
        "start": t0,
        "end": t1,
        "seconds": t1 - t0,
        "bytes": nbytes,
        "bits_per_second": bps,
        "omitted": False,
        "sender": sender,
    }
    if args.udp:
        packets = max(1, nbytes // args.length)
        s["packets"] = packets
        if not sender:
            s.update(jitter_ms=0.21, lost_packets=0, lost_percent=0)
    elif sender:
        s["retransmits"] = 0
    return s


def iperf_start(args: IperfArgs, *, client: bool) -> bytes:
    return _line(
        "start",
        {
            "version": "iperf 3.19.1 (fake)",
            "system_info": "Linux fake 6.10 aarch64",
            "test_start": {
                "protocol": "UDP" if args.udp else "TCP",
                "num_streams": args.parallel,
                "blksize": args.length,
                "duration": args.duration,
                "reverse": int(args.reverse),
                "bidir": int(args.bidir),
            },
            **({"connecting_to": {"host": args.host, "port": args.port}} if client else {}),
        },
    )


def iperf_interval(args: IperfArgs, i: int, *, client: bool) -> bytes:
    """Interval ``i`` (1-based) as the client or the server reports it."""
    bps = args.bitrate * (0.97 + 0.02 * (i % 3))
    t0, t1 = float(i - 1), float(i)
    # The client sends unless reversed; a bidir client also receives.
    sends = (not args.reverse) if client else args.reverse
    data = {"streams": [], "sum": _sum(t0, t1, bps, args, sender=sends)}
    if args.bidir:
        data["sum_bidir_reverse"] = _sum(t0, t1, bps * 0.9, args, sender=not sends)
    return _line("interval", data)


def iperf_end(args: IperfArgs, seconds: float, *, client: bool, interrupted: bool) -> bytes:
    sent = _sum(0.0, seconds, args.bitrate, args, sender=True)
    received = _sum(0.0, seconds, 0 if interrupted and client else args.bitrate, args, False)
    data = {"streams": [], "sum_sent": sent, "sum_received": received}
    if args.bidir:
        data["sum_sent_bidir_reverse"] = sent
        data["sum_received_bidir_reverse"] = received
    data["cpu_utilization_percent"] = {"host_total": 3.1, "remote_total": 2.4}
    return _line("end", data)


def iperf_error(text: str) -> bytes:
    return _line("error", text)
