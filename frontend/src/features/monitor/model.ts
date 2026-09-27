// A monitor's data in the browser: live messages and recorded rows → rows →
// chart series. Pure; the backend's CSV columns and live messages share names
// (see backend services/monitor.py and domain/monitor.py).
import type { ChartData } from '@/ui/charts/types';

type Num = number | null;

export interface Stats { sum: Num; mean: Num; p50: Num; p95: Num; max: Num }

export interface NodeRow {
  t: number;
  target: string;
  kind: 'node' | 'tool';
  purpose?: string | null;
  cpu_pct: Num;
  mem_used: Num;
  mem_limit?: Num;
  pids?: Num;
  oom_kills?: Num;
  rx_bps: Num;
  tx_bps: Num;
  rx_pps?: Num;
  tx_pps?: Num;
  drops?: Num;
  errors?: Num;
}

/** One sweep's host row: host fields, Docker's processes and group totals
 *  flattened (``containerd_shim_rss``, ``node_mem_used``…), as in host.csv. */
export type HostRow = { t: number } & Record<string, number | string | null>;

export interface SweepMessage {
  type: 'sweep';
  t: number;
  step: string;
  /** Host fields (see HOST_FIELDS in the backend) and Docker's processes by name. */
  host: { [key: string]: unknown; infra?: Record<string, { count: number; rss: number; cpu_pct: Num }> };
  groups: Record<string, { count: number; cpu_pct: number; mem_used: number }>;
  selection: {
    count: number;
    cpu_pct: Stats;
    mem_used: Stats;
    rx_bps: Stats;
    tx_bps: Stats;
    top: Record<'cpu_pct' | 'mem_used' | 'net_bps', [string, number][]>;
  };
  nodes: Omit<NodeRow, 't'>[] | null;
  tools: Omit<NodeRow, 't'>[];
  oom: string[];
  missing: string[];
}

export interface Marker { t: number; step?: string; source: string; text: string }

/** Selected-node aggregates per sweep. */
export interface AggRow {
  t: number;
  count: number;
  cpu_mean: Num;
  cpu_p95: Num;
  cpu_max: Num;
  mem_sum: Num;
  mem_mean: Num;
  rx_sum: Num;
  tx_sum: Num;
}

export const GROUPS = ['node', 'tool', 'other_lab', 'other'] as const;
export const INFRA = ['dockerd', 'containerd', 'containerd-shim', 'vde_switch'] as const;

// ── live messages → rows ─────────────────────────────────────────────

export function hostRowFromSweep(m: SweepMessage): HostRow {
  const row: HostRow = { t: m.t, step: m.step };
  for (const [k, v] of Object.entries(m.host)) if (k !== 'infra') row[k] = v as Num;
  for (const [name, v] of Object.entries(m.host.infra ?? {})) {
    const key = name.replace(/-/g, '_');
    row[`${key}_count`] = v.count;
    row[`${key}_rss`] = v.rss;
    row[`${key}_cpu_pct`] = v.cpu_pct;
  }
  for (const [g, v] of Object.entries(m.groups)) {
    row[`${g}_count`] = v.count;
    row[`${g}_cpu_pct`] = v.cpu_pct;
    row[`${g}_mem_used`] = v.mem_used;
  }
  return row;
}

export function aggFromSweep(m: SweepMessage): AggRow {
  const s = m.selection;
  return {
    t: m.t,
    count: s.count,
    cpu_mean: s.cpu_pct.mean,
    cpu_p95: s.cpu_pct.p95,
    cpu_max: s.cpu_pct.max,
    mem_sum: s.mem_used.sum,
    mem_mean: s.mem_used.mean,
    rx_sum: s.rx_bps.sum,
    tx_sum: s.tx_bps.sum,
  };
}

export function nodeRowsFromSweep(m: SweepMessage): NodeRow[] {
  return [...(m.nodes ?? []), ...m.tools].map((r) => ({ ...r, t: m.t }) as NodeRow);
}

// ── recorded rows → aggregates ───────────────────────────────────────

export function percentile(values: number[], q: number): number | null {
  if (!values.length) return null;
  const s = [...values].sort((a, b) => a - b);
  const k = ((s.length - 1) * q) / 100;
  const lo = Math.floor(k);
  const hi = Math.ceil(k);
  return s[lo] + (s[hi] - s[lo]) * (k - lo);
}

const sum = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) : null);

/** Selected-node aggregates per sweep, from recorded node rows. */
export function aggFromNodeRows(rows: readonly NodeRow[]): AggRow[] {
  const byT = new Map<number, NodeRow[]>();
  for (const r of rows) {
    if (r.kind !== 'node') continue;
    const list = byT.get(r.t);
    if (list) list.push(r);
    else byT.set(r.t, [r]);
  }
  return [...byT.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([t, rs]) => {
      const cpu = rs.map((r) => r.cpu_pct).filter((v): v is number => v !== null && v !== undefined);
      const mem = rs.map((r) => r.mem_used).filter((v): v is number => v !== null && v !== undefined);
      return {
        t,
        count: rs.length,
        cpu_mean: cpu.length ? sum(cpu)! / cpu.length : null,
        cpu_p95: percentile(cpu, 95),
        cpu_max: cpu.length ? Math.max(...cpu) : null,
        mem_sum: sum(mem),
        mem_mean: mem.length ? sum(mem)! / mem.length : null,
        rx_sum: sum(rs.map((r) => r.rx_bps ?? 0)),
        tx_sum: sum(rs.map((r) => r.tx_bps ?? 0)),
      };
    });
}

/** Append rows not seen yet (by ``key``), keep them in time order and at most ``limit``. */
export function mergeRows<T extends { t: number }>(into: readonly T[], items: readonly T[], key: (r: T) => string, limit: number): T[] {
  if (!items.length) return into as T[];
  const seen = new Set(into.map(key));
  const fresh = items.filter((r) => !seen.has(key(r)));
  if (!fresh.length) return into as T[];
  const lastT = into.length ? into[into.length - 1].t : -Infinity;
  const merged = fresh.every((r) => r.t >= lastT) ? [...into, ...fresh] : [...into, ...fresh].sort((a, b) => a.t - b.t);
  return merged.length > limit ? merged.slice(merged.length - limit) : merged;
}

// ── chart series ─────────────────────────────────────────────────────

interface Line<T> { key: string; label: string; slot: number; dash?: boolean; value: (r: T) => Num }

/** One series per definition over shared x; series with no values are left out. */
function lines<T extends { t: number }>(rows: readonly T[], defs: readonly Line<T>[]): ChartData {
  const x = rows.map((r) => r.t);
  const series = defs
    .map((d) => ({ key: d.key, label: d.label, slot: d.slot, dash: d.dash, values: rows.map(d.value) }))
    .filter((s) => s.values.some((v) => v !== null && v !== undefined));
  return { x, series };
}

const num = (v: unknown): Num => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const scale = (v: unknown, by: number): Num => {
  const n = num(v);
  return n === null ? null : n / by;
};
const GB = 1e9;

export const hostCpuChart = (rows: readonly HostRow[]) =>
  lines<HostRow>(rows, [{ key: 'cpu', label: 'Host CPU', slot: 1, value: (r) => num(r.vm_cpu_pct) }]);

/** CPU by group, in cores (containers report 100 = one core). */
export const cpuByGroupChart = (rows: readonly HostRow[]) =>
  lines<HostRow>(rows, [
    { key: 'host', label: 'Host (all)', slot: 1, value: (r) => num(r.cores_used) },
    { key: 'node', label: 'Lab nodes', slot: 2, value: (r) => scale(r.node_cpu_pct, 100) },
    { key: 'tool', label: 'AE3GIS tools', slot: 3, value: (r) => scale(r.tool_cpu_pct, 100) },
    { key: 'docker', label: 'Docker daemons', slot: 4, value: (r) => dockerCpu(r) },
    { key: 'other', label: 'Other containers', slot: 5, value: (r) => scale(r.other_cpu_pct, 100) },
  ]);

function dockerCpu(r: HostRow): Num {
  const parts = ['dockerd_cpu_pct', 'containerd_cpu_pct', 'containerd_shim_cpu_pct', 'vde_switch_cpu_pct'].map((k) => num(r[k]));
  return parts.every((p) => p === null) ? null : parts.reduce<number>((a, b) => a + (b ?? 0), 0) / 100;
}

/** Docker's own memory: daemons, a shim per container, a VDE switch per link. */
export function dockerRss(r: HostRow): Num {
  const parts = ['dockerd_rss', 'containerd_rss', 'containerd_shim_rss', 'vde_switch_rss'].map((k) => num(r[k]));
  return parts.every((p) => p === null) ? null : parts.reduce<number>((a, b) => a + (b ?? 0), 0);
}

/** Memory in GB: the host's used total, and what the parts account for. The
 *  gap between the host and the parts is kernel memory (network namespaces,
 *  page tables, buffers) and processes outside containers. */
export const memoryChart = (rows: readonly HostRow[]) =>
  lines<HostRow>(rows, [
    { key: 'host', label: 'Host used', slot: 1, value: (r) => scale(r.mem_used, GB) },
    { key: 'node', label: 'Lab nodes', slot: 2, value: (r) => scale(r.node_mem_used, GB) },
    { key: 'docker', label: 'Docker processes', slot: 4, value: (r) => scale(dockerRss(r), GB) },
    { key: 'tool', label: 'AE3GIS tools', slot: 3, value: (r) => scale(r.tool_mem_used, GB) },
    { key: 'other', label: 'Other containers', slot: 5, value: (r) => scale(r.other_mem_used, GB) },
  ]);

export const pressureChart = (rows: readonly HostRow[]) =>
  lines<HostRow>(rows, [
    { key: 'cpu', label: 'CPU some', slot: 1, value: (r) => num(r.psi_cpu_some) },
    { key: 'mem', label: 'Memory some', slot: 2, value: (r) => num(r.psi_mem_some) },
    { key: 'memfull', label: 'Memory full', slot: 2, dash: true, value: (r) => num(r.psi_mem_full) },
    { key: 'io', label: 'IO some', slot: 3, value: (r) => num(r.psi_io_some) },
  ]);

export const selectionCpuChart = (rows: readonly AggRow[]) =>
  lines<AggRow>(rows, [
    { key: 'mean', label: 'Mean', slot: 1, value: (r) => r.cpu_mean },
    { key: 'p95', label: 'p95', slot: 2, value: (r) => r.cpu_p95 },
    { key: 'max', label: 'Max', slot: 3, dash: true, value: (r) => r.cpu_max },
  ]);

export const selectionNetChart = (rows: readonly AggRow[]) =>
  lines<AggRow>(rows, [
    { key: 'rx', label: 'Received', slot: 1, value: (r) => scale(r.rx_sum, 1e6) },
    { key: 'tx', label: 'Sent', slot: 2, value: (r) => scale(r.tx_sum, 1e6) },
  ]);

export type NodeMetric = 'cpu_pct' | 'mem_used' | 'rx_bps' | 'tx_bps';
const NODE_SCALE: Record<NodeMetric, number> = { cpu_pct: 1, mem_used: 1e6, rx_bps: 1e6, tx_bps: 1e6 };

/** One metric for the ``limit`` busiest nodes (by peak), in a stable order so a
 *  node keeps its colour; ``hidden`` counts the rest. */
export function perNodeChart(
  rows: readonly NodeRow[],
  metric: NodeMetric,
  labelOf: (target: string) => string,
  order: readonly string[],
  limit = 6,
): ChartData & { hidden: number } {
  const byTarget = new Map<string, Map<number, number>>();
  for (const r of rows) {
    if (r.kind !== 'node') continue;
    const v = r[metric];
    if (v === null || v === undefined) continue;
    let m = byTarget.get(r.target);
    if (!m) byTarget.set(r.target, (m = new Map()));
    m.set(r.t, v / NODE_SCALE[metric]);
  }
  const peak = (m: Map<number, number>) => Math.max(0, ...m.values());
  const ranked = [...byTarget.entries()].sort((a, b) => peak(b[1]) - peak(a[1]));
  const pos = (t: string) => {
    const i = order.indexOf(t);
    return i === -1 ? Number.MAX_SAFE_INTEGER : i;
  };
  const shown = ranked.slice(0, limit).sort((a, b) => pos(a[0]) - pos(b[0]));
  const xs = new Set<number>();
  for (const [, m] of shown) for (const t of m.keys()) xs.add(t);
  const x = [...xs].sort((a, b) => a - b);
  return {
    x,
    series: shown.map(([key, m], i) => ({ key, label: labelOf(key), slot: (i % 6) + 1, values: x.map((t) => m.get(t) ?? null) })),
    hidden: Math.max(0, ranked.length - limit),
  };
}

/** The latest row of each node (for the table), busiest CPU first. */
export function latestByNode(rows: readonly NodeRow[]): NodeRow[] {
  const last = new Map<string, NodeRow>();
  for (const r of rows) {
    const prev = last.get(r.target);
    if (!prev || prev.t <= r.t) last.set(r.target, r);
  }
  return [...last.values()].sort((a, b) => (b.cpu_pct ?? 0) - (a.cpu_pct ?? 0));
}

/** How many recorded sweeps to skip so a history fetch stays near ``target`` rows. */
export function everyFor(durationS: number, intervalS: number, target = 900): number {
  if (!(durationS > 0) || !(intervalS > 0)) return 1;
  return Math.max(1, Math.ceil(durationS / intervalS / target));
}
