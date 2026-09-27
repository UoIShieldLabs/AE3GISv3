import { describe, expect, it } from 'vitest';
import type { FlowSample, TrafficTotals } from '@/api/client';
import { latestRates, throughputSeries, totalsSeries } from '../series';

const fs = (flow_id: string, t: number, direction: 'fwd' | 'rev', side: 'sender' | 'receiver', bps: number): FlowSample =>
  ({ flow_id, t, direction, side, bps, bytes: 0, seconds: 1, omitted: false }) as FlowSample;


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

describe('totalsSeries', () => {
  it('charts delivered and, when every flow has a rate, asked', () => {
    const rows: TrafficTotals[] = [
      { t: 1, delivered_bps: 8e6, offered_bps: 10e6, active: 2 },
      { t: 2, delivered_bps: 9e6, offered_bps: null, active: 2 },
    ];
    const data = totalsSeries(rows);
    expect(data.x).toEqual([1, 2]);
    expect(data.series.map((s) => [s.key, s.values])).toEqual([['delivered', [8, 9]], ['offered', [10, null]]]);
    expect(totalsSeries([{ t: 1, delivered_bps: 1e6, offered_bps: null, active: 1 }]).series.map((s) => s.key)).toEqual(['delivered']);
  });
});

describe('latestRates', () => {
  it('reports the latest receiver rate per direction', () => {
    const r = latestRates([fs('f1', 1, 'fwd', 'receiver', 5), fs('f1', 2, 'fwd', 'sender', 9), fs('f1', 2, 'fwd', 'receiver', 7), fs('f1', 2, 'rev', 'sender', 3)]);
    expect(r).toEqual({ f1: { fwd: 7, rev: 3 } });
  });
});
