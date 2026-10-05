import { describe, expect, it } from 'vitest';
import { matrixCells, memoryChart, outcomeTone, stepsLine, summaryLine, timingChart, type BenchSpec, type ScaleEntry } from '../model';

const spread = (mean: number | null) => ({ mean, std: 0, min: mean, max: mean });

const entries: ScaleEntry[] = [
  { scale: 10, runs: 1, ok: 1, deploy_s: spread(3), destroy_s: spread(1), ready_s: spread(0.05), marginal_mem_per_node: spread(15e6), docker_mem_per_node: spread(13e6), node_mem_mean: spread(1.2e6) },
  { scale: 50, runs: 1, ok: 1, deploy_s: spread(12), destroy_s: spread(4), ready_s: spread(null), marginal_mem_per_node: spread(11e6), docker_mem_per_node: spread(12e6), node_mem_mean: spread(1.2e6) },
];

describe('benchmark charts', () => {
  it('plot means against hosts', () => {
    const t = timingChart(entries);
    expect(t.x).toEqual([10, 50]);
    expect(t.series.map((s) => [s.key, s.values])).toEqual([['deploy_s', [3, 12]], ['destroy_s', [1, 4]], ['ready_s', [0.05, null]]]);
    const m = memoryChart(entries);
    expect(m.series.find((s) => s.key === 'marginal_mem_per_node')?.values).toEqual([15, 11]);
  });

  it('summarise a sweep', () => {
    expect(summaryLine({ rows: [{ step: '10 hosts', scale: 10, rep: 1, outcome: 'ok' }], ceiling: 10 }, { scale: [10, 50] })).toBe('1 step of 2 · ceiling 10 hosts');
    expect(summaryLine({ rows: [], reason: 'memory', detail: 'host memory 95%' }, { scale: [10], repetitions: 3 })).toBe('0 steps of 3 · stopped: host memory 95%');
    expect([outcomeTone('ok'), outcomeTone('stopped'), outcomeTone('failed')]).toEqual(['success', 'warning', 'danger']);
  });
});

describe('benchmark kinds', () => {
  const matrix: BenchSpec = {
    kind: 'matrix',
    scale: [100],
    matrix: { patterns: [{ id: 'cs' }, { id: 'mesh' }], axes: { protocol: ['tcp', 'udp'], bitrate: ['50K', '1M'], burst_interval_ms: [100, 2000] } },
  };

  it('describe what each kind runs', () => {
    expect(stepsLine({ scale: [10, 25], repetitions: 3 })).toBe('Scale 10, 25 × 3');
    expect(stepsLine({ adaptive: { start: 400 } })).toBe('Climb from 400 hosts toward 93% memory');
    expect(stepsLine({ kind: 'census', census: { per_image: 5, cases: [{}, {}, {}] } })).toBe('Census of 3 node images, 5 nodes each');
    expect(matrixCells(matrix)).toBe(16);
    expect(stepsLine(matrix)).toBe('Traffic matrix of 16 cells on 100 hosts, deployed once');
  });

  it('summarise climbs, censuses and matrices', () => {
    const row = { step: 's', scale: 100, rep: 1, outcome: 'ok' };
    expect(summaryLine({ rows: [row, row], ceiling: 100, limit: 'memory peaked at 91.0% at 100 hosts' }, { adaptive: { start: 50 } }))
      .toBe('2 steps · ceiling 100 hosts · climb: memory peaked at 91.0% at 100 hosts');
    const census = [{ case: 'a', outcome: 'ok', usable: true }, { case: 'b', outcome: 'skipped', usable: false }];
    expect(summaryLine({ census }, { kind: 'census', census: { cases: [{}, {}, {}] } })).toBe('2 of 3 cases · 1 usable');
    const cells = [{ ...row, cell: { pattern: 'cs' } }, { ...row, cell: { pattern: 'cs' }, outcome: 'degraded' }];
    expect(summaryLine({ rows: [row, ...cells] }, matrix)).toBe('2 of 16 cells · 1 degraded or failed');
  });
});
