// A benchmark's result (backend services/benchmark, domain/benchmark) → the
// sheet's table and scale charts. Pure.
import type { ChartData } from '@/ui/charts/types';

type Num = number | null | undefined;

/** sweep: fixed scales · adaptive: a climb to the host's limit · census: one
 *  step per node image · matrix: traffic cells on one deployment. */
export type BenchKind = 'sweep' | 'adaptive' | 'census' | 'matrix';

export interface BenchRow {
  step: string;
  scale: number;
  rep: number;
  /** A census case (`type · image`) or a matrix cell id. */
  case?: string | null;
  /** A matrix cell's axis values. */
  cell?: Record<string, unknown> | null;
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

export interface CensusEntry {
  case: string;
  outcome: string;
  usable: boolean;
}

export interface CellEntry {
  id: string;
  outcome: string;
}

export interface BenchResult {
  kind?: BenchKind;
  rows?: BenchRow[];
  by_scale?: ScaleEntry[] | null;
  ceiling?: number | null;
  reason?: string | null;
  detail?: string | null;
  stopped_by?: string | null;
  /** How a climb ended (adaptive). */
  limit?: string | null;
  started_at?: string;
  ended_at?: string | null;
  census?: CensusEntry[];
  matrix?: CellEntry[];
}

/** The parts of a benchmark's spec the sheet describes. */
export interface BenchSpec {
  kind?: BenchKind;
  scale?: number[];
  repetitions?: number;
  adaptive?: { start?: number; target_mem_pct?: number } | null;
  census?: { per_image?: number; cases?: unknown[] | null } | null;
  matrix?: { patterns?: { id: string }[]; axes?: Record<string, unknown[]> } | null;
  traffic?: unknown;
}

export const benchKind = (spec: BenchSpec): BenchKind => spec.kind ?? (spec.adaptive ? 'adaptive' : 'sweep');

/** How many cells a matrix makes: its axes multiplied (patterns: all by default). */
export function matrixCells(spec: BenchSpec): number {
  const m = spec.matrix;
  if (!m) return 0;
  const axes = m.axes ?? {};
  let n = axes.pattern?.length ?? m.patterns?.length ?? 1;
  for (const [name, values] of Object.entries(axes)) if (name !== 'pattern') n *= values.length;
  return n * (spec.repetitions ?? 1);
}

/** What the benchmark runs, in one line. */
export function stepsLine(spec: BenchSpec): string {
  const reps = spec.repetitions ?? 1;
  switch (benchKind(spec)) {
    case 'adaptive':
      return `Climb from ${spec.adaptive?.start ?? '?'} hosts toward ${spec.adaptive?.target_mem_pct ?? 93}% memory`;
    case 'census':
      return `Census of ${spec.census?.cases?.length ?? '?'} node images, ${spec.census?.per_image ?? 5} nodes each${reps > 1 ? ` × ${reps}` : ''}`;
    case 'matrix':
      return `Traffic matrix of ${matrixCells(spec)} cells on ${spec.scale?.[0] ?? '?'} hosts, deployed once`;
    default:
      return `Scale ${(spec.scale ?? []).join(', ')} × ${reps}`;
  }
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

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** One line for the list: how far the benchmark got. */
export function summaryLine(result: BenchResult | null | undefined, spec: BenchSpec): string {
  const rows = result?.rows ?? [];
  const parts: string[] = [];
  switch (benchKind(spec)) {
    case 'census': {
      const cases = result?.census ?? [];
      parts.push(`${cases.length} of ${spec.census?.cases?.length ?? '?'} cases`);
      if (cases.length) parts.push(`${cases.filter((c) => c.usable).length} usable`);
      break;
    }
    case 'matrix': {
      const cells = rows.filter((r) => r.cell);
      parts.push(`${cells.length} of ${matrixCells(spec)} cells`);
      const off = cells.filter((r) => r.outcome !== 'ok').length;
      if (off) parts.push(`${off} degraded or failed`);
      break;
    }
    case 'adaptive':
      parts.push(plural(rows.length, 'step'));
      if (result?.ceiling) parts.push(`ceiling ${result.ceiling} hosts`);
      if (result?.limit) parts.push(`climb: ${result.limit}`);
      break;
    default:
      parts.push(`${plural(rows.length, 'step')} of ${(spec.scale?.length ?? 0) * (spec.repetitions ?? 1)}`);
      if (result?.ceiling) parts.push(`ceiling ${result.ceiling} hosts`);
  }
  if (result?.reason) parts.push(`stopped: ${result.detail ?? result.reason}`);
  return parts.join(' · ');
}
