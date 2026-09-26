"""One-line packet summaries for the live capture view (pure; never raises).

Enough of Ethernet / 802.1Q / ARP / IPv4 / IPv6 / TCP / UDP / ICMP to show
who talks to whom and how; full dissection is Wireshark's job (the pcap is
always there). Well-known ports name the application protocol, so ICS traffic
such as Modbus/TCP reads as such.
"""

from __future__ import annotations

import ipaddress
import struct
from dataclasses import asdict, dataclass
from typing import Any

from domain.pcap import LINKTYPE_ETHERNET

PORT_NAMES = {
    20: "FTP-DATA",
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    67: "DHCP",
    68: "DHCP",
    69: "TFTP",
    80: "HTTP",
    102: "S7comm",
    110: "POP3",
    123: "NTP",
    137: "NetBIOS",
    138: "NetBIOS",
    139: "NetBIOS",
    143: "IMAP",
    161: "SNMP",
    162: "SNMP",
    179: "BGP",
    389: "LDAP",
    443: "HTTPS",
    445: "SMB",
    502: "Modbus/TCP",
    514: "Syslog",
    1883: "MQTT",
    2404: "IEC-104",
    3389: "RDP",
    5201: "iperf3",
    8080: "HTTP",
    20000: "DNP3",
    44818: "EtherNet/IP",
    47808: "BACnet",
}

TCP_FLAGS = (
    (0x02, "SYN"),
    (0x10, "ACK"),
    (0x01, "FIN"),
    (0x04, "RST"),
    (0x08, "PSH"),
    (0x20, "URG"),
)

ICMP_TYPES = {
    0: "Echo reply",
    3: "Destination unreachable",
    5: "Redirect",
    8: "Echo request",
    11: "Time exceeded",
}
ICMP6_TYPES = {
    1: "Destination unreachable",
    3: "Time exceeded",
    128: "Echo request",
    129: "Echo reply",
    133: "Router solicitation",
    134: "Router advertisement",
    135: "Neighbor solicitation",
    136: "Neighbor advertisement",
}


@dataclass
class PacketSummary:
    n: int
    ts: float
    len: int
    caplen: int
    src: str = ""
    dst: str = ""
    proto: str = ""
    sport: int | None = None
    dport: int | None = None
    info: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _mac(b: bytes) -> str:
    return ":".join(f"{x:02x}" for x in b)


def _app(proto: str, sport: int, dport: int) -> str:
    return (
        PORT_NAMES.get(min(sport, dport)) or PORT_NAMES.get(dport) or PORT_NAMES.get(sport) or proto
    )


def _tcp(s: PacketSummary, seg: bytes, payload_len: int | None) -> None:
    sport, dport, seq, ack, off_flags, win = struct.unpack_from("!HHIIHH", seg)
    hlen = (off_flags >> 12) * 4
    flags = off_flags & 0x3F
    names = [n for bit, n in TCP_FLAGS if flags & bit]
    length = (payload_len - hlen) if payload_len is not None else max(0, len(seg) - hlen)
    s.sport, s.dport = sport, dport
    s.proto = _app("TCP", sport, dport) if length > 0 else "TCP"
    parts = [f"{sport} → {dport}", f"[{', '.join(names)}]" if names else "[none]", f"Seq={seq}"]
    if flags & 0x10:
        parts.append(f"Ack={ack}")
    parts += [f"Win={win}", f"Len={max(0, length)}"]
    s.info = " ".join(parts)


def _udp(s: PacketSummary, seg: bytes) -> None:
    sport, dport, length = struct.unpack_from("!HHH", seg)
    s.sport, s.dport = sport, dport
    s.proto = _app("UDP", sport, dport)
    s.info = f"{sport} → {dport} Len={max(0, length - 8)}"


def _icmp(s: PacketSummary, seg: bytes, v6: bool) -> None:
    typ, code = seg[0], seg[1]
    names = ICMP6_TYPES if v6 else ICMP_TYPES
    s.proto = "ICMPv6" if v6 else "ICMP"
    text = names.get(typ, f"Type {typ}")
    if typ in ((128, 129) if v6 else (0, 8)) and len(seg) >= 8:
        ident, seq = struct.unpack_from("!HH", seg, 4)
        text += f" id={ident} seq={seq}"
    elif code:
        text += f" (code {code})"
    s.info = text


def _ip_payload(s: PacketSummary, proto: int, seg: bytes, payload_len: int, v6: bool) -> None:
    if proto == 6 and len(seg) >= 20:
        _tcp(s, seg, payload_len)
    elif proto == 17 and len(seg) >= 8:
        _udp(s, seg)
    elif proto in (1, 58) and len(seg) >= 2:
        _icmp(s, seg, v6=proto == 58)
    elif proto == 89:
        s.proto, s.info = "OSPF", "OSPF"
    elif proto == 2:
        s.proto, s.info = "IGMP", "IGMP"
    else:
        s.proto = f"{'IPv6' if v6 else 'IPv4'}/{proto}"
        s.info = f"Protocol {proto}"


def _ipv4(s: PacketSummary, pkt: bytes) -> None:
    ihl = (pkt[0] & 0x0F) * 4
    total, frag = struct.unpack_from("!H2xH", pkt, 2)
    proto = pkt[9]
    s.src = str(ipaddress.IPv4Address(pkt[12:16]))
    s.dst = str(ipaddress.IPv4Address(pkt[16:20]))
    if frag & 0x1FFF:
        s.proto, s.info = "IPv4", f"Fragment offset {(frag & 0x1FFF) * 8}"
        return
    _ip_payload(s, proto, pkt[ihl:], total - ihl, v6=False)


def _ipv6(s: PacketSummary, pkt: bytes) -> None:
    (plen,) = struct.unpack_from("!H", pkt, 4)
    nh = pkt[6]
    s.src = str(ipaddress.IPv6Address(pkt[8:24]))
    s.dst = str(ipaddress.IPv6Address(pkt[24:40]))
    seg, remaining = pkt[40:], plen
    # Skip hop-by-hop / routing / destination options headers.
    while nh in (0, 43, 60) and len(seg) >= 8:
        nh, hlen = seg[0], (seg[1] + 1) * 8
        seg, remaining = seg[hlen:], remaining - hlen
    _ip_payload(s, nh, seg, remaining, v6=True)


def _arp(s: PacketSummary, pkt: bytes) -> None:
    (op,) = struct.unpack_from("!H", pkt, 6)
    sha, spa, tpa = pkt[8:14], pkt[14:18], pkt[24:28]
    s.proto = "ARP"
    s.src = str(ipaddress.IPv4Address(spa))
    s.dst = str(ipaddress.IPv4Address(tpa))
    if op == 1:
        s.info = f"Who has {s.dst}? Tell {s.src}"
    elif op == 2:
        s.info = f"{s.src} is at {_mac(sha)}"
    else:
        s.info = f"Opcode {op}"


def summarize(n: int, ts: float, data: bytes, origlen: int, linktype: int | None) -> PacketSummary:
    s = PacketSummary(n=n, ts=ts, len=origlen, caplen=len(data))
    try:
        if linktype != LINKTYPE_ETHERNET:
            s.proto, s.info = "?", f"Link type {linktype} (open the pcap in Wireshark)"
            return s
        s.src, s.dst = _mac(data[6:12]), _mac(data[0:6])
        (etype,) = struct.unpack_from("!H", data, 12)
        off = 14
        vlan = None
        while etype in (0x8100, 0x88A8):
            vlan = struct.unpack_from("!H", data, off)[0] & 0x0FFF
            (etype,) = struct.unpack_from("!H", data, off + 2)
            off += 4
        payload = data[off:]
        if etype == 0x0800:
            _ipv4(s, payload)
        elif etype == 0x86DD:
            _ipv6(s, payload)
        elif etype == 0x0806:
            _arp(s, payload)
        elif etype == 0x88CC:
            s.proto, s.info = "LLDP", "Link Layer Discovery Protocol"
        elif etype < 0x0600 and data[0:6] == b"\x01\x80\xc2\x00\x00\x00":
            s.proto, s.info = "STP", "Spanning Tree"
        else:
            s.proto, s.info = f"0x{etype:04x}", f"Ethertype 0x{etype:04x}"
        if vlan is not None:
            s.info = f"VLAN {vlan} · {s.info}"
    except (struct.error, IndexError, ValueError):
        s.info = (s.info + " " if s.info else "") + "[truncated]"
        s.proto = s.proto or "?"
    return s
