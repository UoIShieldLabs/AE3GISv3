"""Classic pcap stream framing (pure; no I/O).

``tcpdump -w -`` writes a 24-byte global header, then records: a 16-byte
record header (timestamp seconds, µs or ns fraction, captured length, original
length) followed by the captured bytes. Chunks from a pipe split records
anywhere; ``PcapSplitter`` reassembles them so every record reaching the file
and the live view is whole, which also means a file cut at any record boundary
is a valid capture.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

MAGIC_US = 0xA1B2C3D4
MAGIC_NS = 0xA1B23C4D
LINKTYPE_ETHERNET = 1
LINKTYPE_LINUX_SLL = 113
LINKTYPE_LINUX_SLL2 = 276

GLOBAL_HEADER_LEN = 24
RECORD_HEADER_LEN = 16
# tcpdump's default snaplen; a record claiming more than this is corruption.
MAX_SNAPLEN = 262144


class PcapError(ValueError):
    """The stream is not a pcap, or a record header is corrupt."""


def global_header(snaplen: int = MAX_SNAPLEN, linktype: int = LINKTYPE_ETHERNET) -> bytes:
    """A little-endian, microsecond pcap global header."""
    return struct.pack("<IHHiIII", MAGIC_US, 2, 4, 0, 0, snaplen, linktype)


def record(ts: float, data: bytes, orig_len: int | None = None) -> bytes:
    """One little-endian microsecond record (header + data)."""
    sec = int(ts)
    usec = int(round((ts - sec) * 1_000_000))
    if usec >= 1_000_000:
        sec, usec = sec + 1, usec - 1_000_000
    return struct.pack("<IIII", sec, usec, len(data), orig_len or len(data)) + data


@dataclass
class Record:
    ts: float
    caplen: int
    origlen: int
    data: bytes
    raw: bytes  # record header + data, exactly as it appeared in the stream


class PcapSplitter:
    """Feed arbitrary chunks of a pcap stream; get back whole records."""

    def __init__(self) -> None:
        self._buf = bytearray()
        self.header: bytes | None = None
        self.linktype: int | None = None
        self.snaplen = MAX_SNAPLEN
        self._endian = "<"
        self._frac = 1_000_000

    def feed(self, chunk: bytes) -> list[Record]:
        self._buf.extend(chunk)
        out: list[Record] = []
        if self.header is None:
            if len(self._buf) < GLOBAL_HEADER_LEN:
                return out
            self._parse_global(bytes(self._buf[:GLOBAL_HEADER_LEN]))
            del self._buf[:GLOBAL_HEADER_LEN]
        fmt = self._endian + "IIII"
        limit = max(self.snaplen, MAX_SNAPLEN)
        pos = 0
        buf = self._buf
        while len(buf) - pos >= RECORD_HEADER_LEN:
            sec, frac, caplen, origlen = struct.unpack_from(fmt, buf, pos)
            if caplen > limit:
                raise PcapError(f"Corrupt record: {caplen} captured bytes > snaplen {limit}")
            end = pos + RECORD_HEADER_LEN + caplen
            if end > len(buf):
                break
            raw = bytes(buf[pos:end])
            out.append(
                Record(
                    ts=sec + frac / self._frac,
                    caplen=caplen,
                    origlen=origlen,
                    data=raw[RECORD_HEADER_LEN:],
                    raw=raw,
                )
            )
            pos = end
        if pos:
            del buf[:pos]
        return out

    @property
    def pending(self) -> int:
        """Bytes held back waiting for the rest of a record."""
        return len(self._buf)

    def _parse_global(self, header: bytes) -> None:
        for endian in ("<", ">"):
            (magic,) = struct.unpack(endian + "I", header[:4])
            if magic in (MAGIC_US, MAGIC_NS):
                self._endian = endian
                self._frac = 1_000_000_000 if magic == MAGIC_NS else 1_000_000
                break
        else:
            raise PcapError(f"Not a pcap stream (magic {header[:4].hex()})")
        _, _, _, _, snaplen, linktype = struct.unpack(self._endian + "HHiIII", header[4:])
        self.header = header
        self.snaplen = snaplen or MAX_SNAPLEN
        self.linktype = linktype & 0x0FFFFFFF
