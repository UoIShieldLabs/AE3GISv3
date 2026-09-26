import type { PacketSummary } from '@/api/client';

/** Most rows the live view keeps; the pcap has everything. */
export const MAX_ROWS = 5000;

/** Append new packets (deduped by number, in order), keeping the last `max`. */
export function appendPackets(rows: readonly PacketSummary[], incoming: readonly PacketSummary[], max = MAX_ROWS): PacketSummary[] {
  if (incoming.length === 0) return rows as PacketSummary[];
  const last = rows.length ? rows[rows.length - 1].n : 0;
  const fresh = incoming.filter((p) => p.n > last);
  if (fresh.length === 0) return rows as PacketSummary[];
  const next = rows.concat(fresh);
  return next.length > max ? next.slice(next.length - max) : next;
}

/** Case-insensitive match over the visible columns; empty matches everything. */
export function matchesFilter(p: PacketSummary, filter: string): boolean {
  const q = filter.trim().toLowerCase();
  if (!q) return true;
  return q.split(/\s+/).every((term) =>
    [p.src, p.dst, p.proto, p.info, String(p.sport ?? ''), String(p.dport ?? '')].some((v) => (v ?? '').toLowerCase().includes(term)),
  );
}

export function formatBytes(n: number | null | undefined): string {
  if (!n) return '0 B';
  const units = ['B', 'kB', 'MB', 'GB'];
  let i = 0;
  let v = n;
  while (v >= 1000 && i < units.length - 1) { v /= 1000; i += 1; }
  return `${v >= 100 || i === 0 ? v.toFixed(0) : v.toFixed(1)} ${units[i]}`;
}

export function formatBps(bps: number | null | undefined): string {
  if (!bps) return '0 b/s';
  const units = ['b/s', 'kb/s', 'Mb/s', 'Gb/s'];
  let i = 0;
  let v = bps;
  while (v >= 1000 && i < units.length - 1) { v /= 1000; i += 1; }
  return `${v >= 100 || i === 0 ? v.toFixed(0) : v.toFixed(1)} ${units[i]}`;
}
