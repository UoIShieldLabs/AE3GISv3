import { describe, expect, it } from 'vitest';
import { flowErrors, newFlow, nextFlowId, toRequestFlow } from '../flows';

describe('flows', () => {
  it('numbers new flows after the ones in use', () => {
    const a = newFlow([], 'hA', 'hB');
    expect(a.id).toBe('f1');
    expect(nextFlowId([a, { ...a, id: 'f3' }])).toBe('f2');
  });

  it('reports what keeps a flow from running', () => {
    const ok = newFlow([], 'hA', 'hB');
    expect(flowErrors([ok])).toEqual({});
    expect(flowErrors([{ ...ok, server: 'hA' }]).f1).toMatch(/differ/);
    expect(flowErrors([{ ...ok, client: '' }]).f1).toMatch(/Pick/);
    expect(flowErrors([{ ...ok, bitrate: 'fast' }]).f1).toMatch(/Bitrate/);
    expect(flowErrors([{ ...ok, bitrate: '50M' }])).toEqual({});
  });

  it('builds the API flow', () => {
    expect(toRequestFlow({ ...newFlow([], 'hA', 'hB'), protocol: 'udp', bitrate: '20M' })).toMatchObject({
      generator: 'iperf3', id: 'f1', client: 'hA', server: 'hB', protocol: 'udp', bitrate: '20M', parallel: 1, direction: 'forward',
    });
    expect(toRequestFlow(newFlow([], 'hA', 'hB')).bitrate).toBeNull();
  });
});
