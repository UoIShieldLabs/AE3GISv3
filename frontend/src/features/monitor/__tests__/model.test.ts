import { beforeEach, describe, expect, it } from 'vitest';
import { applyCatalog } from '@/catalog/catalog';
import { CATALOG } from '@/test/catalogFixture';
import type { TopologyData } from '@/types/topology';
import {
  aggFromNodeRows,
  aggFromSweep,
  cpuByGroupChart,
  everyFor,
  hostRowFromSweep,
  latestByNode,
  memoryChart,
  mergeRows,
  nodeRowsFromSweep,
  percentile,
  perNodeChart,
  type NodeRow,
  type SweepMessage,
} from '../model';
import { nodesOf, preview, toRequest } from '../selection';

const stats = (v: number) => ({ sum: v * 2, mean: v, p50: v, p95: v, max: v });

const sweep = (t: number, extra: Partial<SweepMessage> = {}): SweepMessage => ({
  type: 'sweep',
  t,
  step: '',
  host: { vm_cpu_pct: 20, cores_used: 1.6, mem_used: 3e9, mem_total: 8e9, infra: { 'containerd-shim': { count: 9, rss: 120e6, cpu_pct: 2 }, dockerd: { count: 1, rss: 140e6, cpu_pct: 3 } } },
  groups: { node: { count: 6, cpu_pct: 50, mem_used: 10e6 }, tool: { count: 1, cpu_pct: 1, mem_used: 8e6 }, other_lab: { count: 0, cpu_pct: 0, mem_used: 0 }, other: { count: 1, cpu_pct: 10, mem_used: 200e6 } },
  selection: { count: 2, cpu_pct: stats(5), mem_used: stats(1e6), rx_bps: stats(1e3), tx_bps: stats(2e3), top: { cpu_pct: [['a', 6]], mem_used: [['a', 1e6]], net_bps: [['a', 3e3]] } },
  nodes: [{ target: 'a', kind: 'node', cpu_pct: 6, mem_used: 1e6, rx_bps: 1e3, tx_bps: 2e3 }],
  tools: [{ target: 'ae3gis-collector-1', kind: 'tool', purpose: 'collector', cpu_pct: 1, mem_used: 8e6, rx_bps: null, tx_bps: null }],
  oom: [],
  missing: [],
  ...extra,
});

const row = (t: number, target: string, cpu: number, mem = 1e6, rx = 0): NodeRow => ({ t, target, kind: 'node', cpu_pct: cpu, mem_used: mem, rx_bps: rx, tx_bps: 0 });

describe('live sweeps → rows', () => {
  it('flattens the host like host.csv', () => {
    const r = hostRowFromSweep(sweep(3));
    expect(r).toMatchObject({ t: 3, vm_cpu_pct: 20, containerd_shim_count: 9, containerd_shim_rss: 120e6, dockerd_cpu_pct: 3, node_cpu_pct: 50, other_mem_used: 200e6 });
    expect(r.infra).toBeUndefined();
    expect(aggFromSweep(sweep(3))).toMatchObject({ t: 3, count: 2, cpu_mean: 5, mem_sum: 2e6, rx_sum: 2e3 });
    expect(nodeRowsFromSweep(sweep(3)).map((n) => [n.t, n.target, n.kind])).toEqual([[3, 'a', 'node'], [3, 'ae3gis-collector-1', 'tool']]);
  });

  it('charts CPU in cores and memory by part', () => {
    const rows = [hostRowFromSweep(sweep(1)), hostRowFromSweep(sweep(2))];
    const cpu = cpuByGroupChart(rows);
    expect(cpu.series.map((s) => [s.key, s.values[0]])).toEqual([['host', 1.6], ['node', 0.5], ['tool', 0.01], ['docker', 0.05], ['other', 0.1]]);
    const mem = memoryChart(rows);
    expect(mem.series.find((s) => s.key === 'docker')?.values[0]).toBeCloseTo(0.26);
    expect(mem.x).toEqual([1, 2]);
  });
});

describe('recorded rows', () => {
  it('aggregates node rows per sweep', () => {
    const agg = aggFromNodeRows([row(2, 'a', 10, 2e6, 5), row(1, 'a', 4), row(1, 'b', 8), { ...row(1, 't', 99), kind: 'tool' }]);
    expect(agg.map((a) => [a.t, a.count, a.cpu_mean, a.cpu_max, a.mem_sum])).toEqual([[1, 2, 6, 8, 2e6], [2, 1, 10, 10, 2e6]]);
    expect(percentile([1, 2, 3, 4], 50)).toBe(2.5);
    expect(percentile([], 95)).toBeNull();
  });

  it('merges without duplicates, in order, within a limit', () => {
    const key = (r: { t: number }) => String(r.t);
    const a = mergeRows([{ t: 1 }, { t: 2 }], [{ t: 2 }, { t: 3 }], key, 10);
    expect(a.map((r) => r.t)).toEqual([1, 2, 3]);
    expect(mergeRows(a, [{ t: 0 }], key, 3).map((r) => r.t)).toEqual([1, 2, 3]);
    expect(mergeRows([{ t: 5 }], [{ t: 4 }], key, 10).map((r) => r.t)).toEqual([4, 5]);
  });

  it('charts the busiest nodes in a stable order', () => {
    const rows = [row(1, 'a', 1), row(1, 'b', 50), row(1, 'c', 20), row(2, 'a', 2), row(2, 'b', 40)];
    const data = perNodeChart(rows, 'cpu_pct', (t) => t.toUpperCase(), ['a', 'b', 'c'], 2);
    expect(data.series.map((s) => [s.label, s.slot, s.values])).toEqual([['B', 1, [50, 40]], ['C', 2, [20, null]]]);
    expect(data.hidden).toBe(1);
    expect(latestByNode(rows).map((r) => [r.target, r.t])).toEqual([['b', 2], ['c', 1], ['a', 2]]);
  });

  it('downsamples long histories', () => {
    expect(everyFor(60, 1)).toBe(1);
    expect(everyFor(3600, 1)).toBe(4);
    expect(everyFor(0, 1)).toBe(1);
  });
});

describe('selection', () => {
  beforeEach(() => applyCatalog(CATALOG));

  const topology = {
    name: 't',
    sites: [
      {
        id: 's', name: 'S', location: '', position: { x: 0, y: 0 },
        subnets: [
          { id: 'n1', name: 'N1', cidr: '10.0.1.0/24', containers: [{ id: 'r', name: 'R', type: 'router', ip: '10.0.1.1' }, { id: 'h1', name: 'H1', type: 'gizmo', ip: '10.0.1.5' }], connections: [] },
          { id: 'n2', name: 'N2', cidr: '10.0.2.0/24', containers: [{ id: 'r', name: 'R', type: 'router', ip: '10.0.2.1' }, { id: 'h2', name: 'H2', type: 'gizmo', ip: '10.0.2.5' }], connections: [] },
        ],
        subnetConnections: [],
      },
    ],
    siteConnections: [],
  } as unknown as TopologyData;

  it('previews what the backend will resolve', () => {
    const nodes = nodesOf(topology);
    expect(nodes.find((n) => n.id === 'r')?.subnetIds).toEqual(['n1', 'n2']);
    const running = (id: string) => id !== 'h2';
    const ids = (mode: Parameters<typeof toRequest>[0]) => preview(nodes, running, mode).map((n) => n.id);
    expect(ids({ mode: 'all', picks: [] })).toEqual(['r', 'h1']);
    expect(ids({ mode: 'hosts', picks: [] })).toEqual(['h1']);
    expect(ids({ mode: 'subnets', picks: ['n2'] })).toEqual(['r']);
    expect(ids({ mode: 'types', picks: ['router'] })).toEqual(['r']);
    expect(ids({ mode: 'nodes', picks: ['h1', 'h2'] })).toEqual(['h1']);
    expect(toRequest({ mode: 'hosts', picks: [] })).toEqual({ roles: ['host'] });
    expect(toRequest({ mode: 'subnets', picks: ['n1'] })).toEqual({ subnets: ['n1'] });
    expect(toRequest({ mode: 'nodes', picks: ['h1'] })).toEqual(['h1']);
  });
});
