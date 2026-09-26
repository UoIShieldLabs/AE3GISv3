// Pure transforms from traffic samples to chart-ready, x-aligned series.
import type { FlowSample, NodeSample } from '@/api/client';
import type { ChartData } from '@/ui/charts/types';

export type { ChartData, ChartSeries } from '@/ui/charts/types';

const round = (t: number) => Math.round(t * 10) / 10;

function align(rows: { key: string; points: Map<number, number> }[]): { x: number[]; values: Map<string, (number | null)[]> } {
  const xs = new Set<number>();
  for (const r of rows) for (const t of r.points.keys()) xs.add(t);
  const x = [...xs].sort((a, b) => a - b);
  const values = new Map<string, (number | null)[]>();
  for (const r of rows) values.set(r.key, x.map((t) => r.points.get(t) ?? null));
  return { x, values };
}

/** Throughput per flow and direction in Mb/s, as the receiver measured it
 *  (the sender's figure when there is no receiver sample). Each flow keeps
 *  its slot (its position in the run); the reverse direction is dashed. */
export function throughputSeries(samples: readonly FlowSample[], flowIds: readonly string[]): ChartData {
  const rows: { key: string; label: string; slot: number; dash: boolean; points: Map<number, number> }[] = [];
  flowIds.forEach((id, i) => {
    for (const direction of ['fwd', 'rev'] as const) {
      const mine = samples.filter((s) => s.flow_id === id && s.direction === direction && !s.omitted);
      if (!mine.length) continue;
      const rx = mine.filter((s) => s.side === 'receiver');
      const use = rx.length ? rx : mine;
      rows.push({
        key: `${id}:${direction}`,
        label: `${id} ${direction === 'fwd' ? '→' : '←'}`,
        slot: (i % 6) + 1,
        dash: direction === 'rev',
        points: new Map(use.map((s) => [round(s.t), s.bps / 1e6])),
      });
    }
  });
  const { x, values } = align(rows);
  return { x, series: rows.map((r) => ({ key: r.key, label: r.label, slot: r.slot, dash: r.dash, values: values.get(r.key)! })) };
}

export type NodeMetric = 'cpu' | 'mem' | 'rx' | 'tx';

export function metricOf(s: NodeSample, metric: NodeMetric): number | null {
  switch (metric) {
    case 'cpu':
      return s.cpu_percent ?? null;
    case 'mem':
      return s.mem_used / 1e6;
    case 'rx':
    case 'tx': {
      const ifaces = Object.values(s.ifaces ?? {});
      if (!ifaces.length) return null;
      return ifaces.reduce((sum, i) => sum + (metric === 'rx' ? i.rx_bps : i.tx_bps), 0) / 1e6;
    }
  }
}

/** One metric for the `limit` busiest targets (by peak), plus how many were left out.
 *  Slots follow the target's position in `order` so a target keeps its colour. */
export function nodeSeries(
  samples: readonly NodeSample[],
  metric: NodeMetric,
  labelOf: (target: string) => string,
  order: readonly string[],
  limit = 6,
): ChartData & { hidden: number } {
  const byTarget = new Map<string, Map<number, number>>();
  for (const s of samples) {
    const v = metricOf(s, metric);
    if (v === null) continue;
    let m = byTarget.get(s.target);
    if (!m) byTarget.set(s.target, (m = new Map()));
    m.set(round(s.t), v);
  }
  const peak = (m: Map<number, number>) => Math.max(0, ...m.values());
  const ranked = [...byTarget.entries()].sort((a, b) => peak(b[1]) - peak(a[1]));
  const shown = ranked.slice(0, limit).sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]));
  const { x, values } = align(shown.map(([key, points]) => ({ key, points })));
  return {
    x,
    series: shown.map(([key], i) => ({ key, label: labelOf(key), slot: (i % 6) + 1, values: values.get(key)! })),
    hidden: Math.max(0, ranked.length - limit),
  };
}

/** Latest receiver rate per flow direction, in b/s. */
export function latestRates(samples: readonly FlowSample[]): Record<string, { fwd?: number; rev?: number }> {
  const out: Record<string, { fwd?: number; rev?: number; tf?: number; tr?: number }> = {};
  for (const s of samples) {
    const o = (out[s.flow_id] ??= {});
    const tKey = s.direction === 'fwd' ? 'tf' : 'tr';
    const prefer = s.side === 'receiver';
    if ((o[tKey] ?? -1) < s.t || (prefer && (o[tKey] ?? -1) <= s.t)) {
      o[s.direction] = s.bps;
      o[tKey] = s.t;
    }
  }
  return Object.fromEntries(Object.entries(out).map(([k, v]) => [k, { fwd: v.fwd, rev: v.rev }]));
}
