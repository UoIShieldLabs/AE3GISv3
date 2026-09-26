import { describe, expect, it } from 'vitest';
import type { PacketSummary } from '@/api/client';
import { appendPackets, formatBps, formatBytes, matchesFilter } from '../packetBuffer';
import { detectPlatform, tcpdumpCommand, wiresharkCommand } from '../wiresharkCommand';

const pkt = (n: number, over: Partial<PacketSummary> = {}): PacketSummary => ({ n, ts: n, len: 60, caplen: 60, src: '10.0.1.5', dst: '10.0.2.5', proto: 'ICMP', info: 'Echo request', ...over });

describe('packet buffer', () => {
  it('appends in order, drops duplicates and keeps the newest', () => {
    let rows = appendPackets([], [pkt(1), pkt(2)]);
    rows = appendPackets(rows, [pkt(2), pkt(3), pkt(4)], 3);
    expect(rows.map((p) => p.n)).toEqual([2, 3, 4]);
    expect(appendPackets(rows, [])).toBe(rows);
  });

  it('filters on every visible column, all terms must match', () => {
    const p = pkt(1, { proto: 'Modbus/TCP', sport: 40000, dport: 502, info: 'ACK' });
    expect(matchesFilter(p, 'modbus 502')).toBe(true);
    expect(matchesFilter(p, '10.0.2.5')).toBe(true);
    expect(matchesFilter(p, 'modbus arp')).toBe(false);
    expect(matchesFilter(p, '  ')).toBe(true);
  });

  it('formats sizes and rates', () => {
    expect(formatBytes(1_620)).toBe('1.6 kB');
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBps(88_000_000)).toBe('88.0 Mb/s');
  });
});

describe('wireshark command', () => {
  const url = 'http://localhost:3000/api/v1/captures/abc/pcap?follow=true';
  it('streams into the local Wireshark per platform', () => {
    expect(wiresharkCommand(url, 'mac')).toBe(`curl -sN '${url}' | /Applications/Wireshark.app/Contents/MacOS/Wireshark -k -i -`);
    expect(wiresharkCommand(url, 'linux')).toBe(`curl -sN '${url}' | wireshark -k -i -`);
    expect(wiresharkCommand(url, 'windows')).toContain('curl.exe -sN "');
    expect(tcpdumpCommand(url, 'linux')).toBe(`curl -sN '${url}' | tcpdump -nn -r -`);
  });

  it('detects the platform', () => {
    expect(detectPlatform('Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)')).toBe('mac');
    expect(detectPlatform('Mozilla/5.0 (Windows NT 10.0; Win64; x64)')).toBe('windows');
    expect(detectPlatform('Mozilla/5.0 (X11; Linux x86_64)')).toBe('linux');
  });
});
