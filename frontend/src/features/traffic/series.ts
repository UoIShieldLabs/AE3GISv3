// Pure transforms from traffic samples to chart-ready, x-aligned series.
import type { FlowSample, TrafficTotals } from '@/api/client';
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

/** All flows together in Mb/s: what arrived (receiver-measured) and, when every
 *  running flow has a target rate, what was asked (dashed). */
export function totalsSeries(totals: readonly TrafficTotals[]): ChartData {
  const x = totals.map((r) => round(r.t));
  const series = [
    { key: 'delivered', label: 'Delivered', slot: 1, values: totals.map((r) => r.delivered_bps / 1e6) },
    { key: 'offered', label: 'Asked', slot: 2, dash: true, values: totals.map((r) => (r.offered_bps === null || r.offered_bps === undefined ? null : r.offered_bps / 1e6)) },
  ].filter((sr) => sr.values.some((v) => v !== null));
  return { x, series };
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
