import { describe, expect, it } from 'vitest';
import type { FlowSample, NodeSample } from '@/api/client';
import { latestRates, metricOf, nodeSeries, throughputSeries } from '../series';

const fs = (flow_id: string, t: number, direction: 'fwd' | 'rev', side: 'sender' | 'receiver', bps: number): FlowSample =>
  ({ flow_id, t, direction, side, bps, bytes: 0, seconds: 1, omitted: false }) as FlowSample;

const ns = (target: string, t: number, cpu: number | null, mem = 10e6): NodeSample =>
  ({ target, t, kind: 'node', cpu_percent: cpu, mem_used: mem, ifaces: { eth0: { rx_bps: 2e6, tx_bps: 1e6, rx_pps: 0, tx_pps: 0, rx_dropped: 0, tx_dropped: 0, errors: 0 } } }) as NodeSample;

describe('throughputSeries', () => {
  it('prefers the receiver, aligns x and dashes the reverse direction', () => {
    const data = throughputSeries(
      [fs('f1', 1.0, 'fwd', 'sender', 90e6), fs('f1', 1.02, 'fwd', 'receiver', 80e6), fs('f1', 2.0, 'fwd', 'receiver', 70e6), fs('f2', 1.5, 'rev', 'sender', 10e6)],
      ['f1', 'f2'],
    );
    expect(data.x).toEqual([1, 1.5, 2]);
    const [f1, f2] = data.series;
    expect(f1).toMatchObject({ key: 'f1:fwd', slot: 1, dash: false, values: [80, null, 70] });
    expect(f2).toMatchObject({ key: 'f2:rev', slot: 2, dash: true, values: [null, 10, null] });
  });

  it('keeps a flow on its slot when another has no samples yet', () => {
    const data = throughputSeries([fs('f2', 1, 'fwd', 'receiver', 1e6)], ['f1', 'f2']);
    expect(data.series.map((s) => s.slot)).toEqual([2]);
  });
});

describe('nodeSeries', () => {
  it('shows the busiest targets in a stable order and counts the rest', () => {
    const samples = [ns('a', 1, 5), ns('b', 1, 50), ns('c', 1, 20), ns('a', 2, 6), ns('b', 2, null)];
    const data = nodeSeries(samples, 'cpu', (t) => t.toUpperCase(), ['a', 'b', 'c'], 2);
    expect(data.series.map((s) => s.label)).toEqual(['B', 'C']);
    expect(data.hidden).toBe(1);
    expect(data.x).toEqual([1]); // only the shown targets' samples set the x axis
    expect(data.series[0].values).toEqual([50]);
  });

  it('computes memory and interface rates', () => {
    const s = ns('a', 1, 1, 42e6);
    expect(metricOf(s, 'mem')).toBe(42);
    expect(metricOf(s, 'rx')).toBe(2);
    expect(metricOf({ ...s, ifaces: {} }, 'tx')).toBeNull();
  });
});

describe('latestRates', () => {
  it('reports the latest receiver rate per direction', () => {
    const r = latestRates([fs('f1', 1, 'fwd', 'receiver', 5), fs('f1', 2, 'fwd', 'sender', 9), fs('f1', 2, 'fwd', 'receiver', 7), fs('f1', 2, 'rev', 'sender', 3)]);
    expect(r).toEqual({ f1: { fwd: 7, rev: 3 } });
  });
});
