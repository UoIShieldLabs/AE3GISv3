// A benchmark's result (backend services/benchmark, domain/benchmark) → the
// sheet's table and scale charts. Pure.
import type { ChartData } from '@/ui/charts/types';

type Num = number | null | undefined;

export interface BenchRow {
  step: string;
  scale: number;
  rep: number;
  outcome: 'ok' | 'stopped' | 'failed' | 'degraded' | string;
  reason?: string | null;
  detail?: string | null;
  nodes?: number;
  links?: number;
  deploy_s?: Num;
  ready_s?: Num;
  destroy_s?: Num;
  marginal_mem_per_node?: Num;
  docker_mem_per_node?: Num;
  node_mem_mean?: Num;
  hold_cpu_mean?: Num;
  /** dockerd + containerd + shims + VDE switches over the hold window, 100 = one core. */
  hold_docker_cpu_mean?: Num;
  hold_mem_pct_max?: Num;
  hold_psi_mem_full_max?: Num;
  delivered_ratio?: Num;
  flows?: Num;
}

interface Spread { mean: Num; std: Num; min: Num; max: Num }

export interface ScaleEntry {
  scale: number;
  runs: number;
  ok: number;
  nodes?: number;
  [metric: string]: Spread | number | undefined;
}

export interface BenchResult {
  rows?: BenchRow[];
  by_scale?: ScaleEntry[];
  ceiling?: number | null;
  reason?: string | null;
  detail?: string | null;
  stopped_by?: string | null;
  started_at?: string;
  ended_at?: string | null;
}

const meanOf = (e: ScaleEntry, key: string): number | null => {
  const v = e[key];
  return typeof v === 'object' && v !== null && typeof v.mean === 'number' ? v.mean : null;
};

function perScale(entries: readonly ScaleEntry[], lines: { key: string; label: string; slot: number; scale?: number; dash?: boolean }[]): ChartData {
  const x = entries.map((e) => e.scale);
  const series = lines
    .map((l) => ({
      key: l.key,
      label: l.label,
      slot: l.slot,
      dash: l.dash,
      values: entries.map((e) => {
        const v = meanOf(e, l.key);
        return v === null ? null : v / (l.scale ?? 1);
      }),
    }))
    .filter((s) => s.values.some((v) => v !== null));
  return { x, series };
}

/** Deploy, ready and destroy seconds per scale (mean over repetitions). */
export const timingChart = (entries: readonly ScaleEntry[]) =>
  perScale(entries, [
    { key: 'deploy_s', label: 'Deploy', slot: 1 },
    { key: 'destroy_s', label: 'Destroy', slot: 2 },
    { key: 'ready_s', label: 'Network ready', slot: 3, dash: true },
  ]);

/** Memory per node (MB): what the host lost, Docker's share, the container's own figure. */
export const memoryChart = (entries: readonly ScaleEntry[]) =>
  perScale(entries, [
    { key: 'marginal_mem_per_node', label: 'Host memory', slot: 1, scale: 1e6 },
    { key: 'docker_mem_per_node', label: 'Docker processes', slot: 4, scale: 1e6 },
    { key: 'node_mem_mean', label: 'Node cgroup', slot: 2, scale: 1e6, dash: true },
  ]);

export function outcomeTone(outcome: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (outcome === 'ok') return 'success';
  if (outcome === 'degraded' || outcome === 'stopped') return 'warning';
  if (outcome === 'failed') return 'danger';
  return 'neutral';
}

/** One line for the list: how far the sweep got. */
export function summaryLine(result: BenchResult | null | undefined, scale: readonly number[]): string {
  const rows = result?.rows ?? [];
  const parts = [`${rows.length} step${rows.length === 1 ? '' : 's'} of ${scale.length}`];
  if (result?.ceiling) parts.push(`ceiling ${result.ceiling} hosts`);
  if (result?.reason) parts.push(`stopped: ${result.detail ?? result.reason}`);
  return parts.join(' · ');
}
