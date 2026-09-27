import { describe, expect, it } from 'vitest';
import { memoryChart, outcomeTone, summaryLine, timingChart, type ScaleEntry } from '../model';

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
    expect(summaryLine({ rows: [{ step: '10 hosts', scale: 10, rep: 1, outcome: 'ok' }], ceiling: 10 }, [10, 50])).toBe('1 step of 2 · ceiling 10 hosts');
    expect(summaryLine({ rows: [], reason: 'memory', detail: 'host memory 95%' }, [10])).toBe('0 steps of 1 · stopped: host memory 95%');
    expect([outcomeTone('ok'), outcomeTone('stopped'), outcomeTone('failed')]).toEqual(['success', 'warning', 'danger']);
  });
});
