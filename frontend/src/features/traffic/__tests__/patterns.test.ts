import { describe, expect, it } from 'vitest';
import { flowCount, newPattern, patternError, toRequestPattern, type NodeSet } from '../patterns';

const HOSTS = ['a', 'b', 'c', 'd'];
const resolve = (set: NodeSet, picks: string[]) => (set === 'pick' ? picks.filter((p) => HOSTS.includes(p) || p === 'r') : set === 'all' ? [...HOSTS, 'r'] : HOSTS);

describe('traffic pattern drafts', () => {
  it('count the flows the backend will make', () => {
    const cs = { ...newPattern('clients_to_servers'), servers: ['a'] };
    expect(flowCount(cs, resolve)).toBe(3); // the server is not its own client
    expect(flowCount({ ...cs, servers: ['a', 'b'], each: 'all' }, resolve)).toBe(4);
    const mesh = { ...newPattern('mesh'), fanout: 2 };
    expect(flowCount(mesh, resolve)).toBe(8);
    expect(flowCount({ ...mesh, fanout: 9 }, resolve)).toBe(12); // capped at a full mesh
    expect(flowCount({ ...mesh, nodeSet: 'pick', nodes: ['a'] }, resolve)).toBe(0);
  });

  it('turn into request patterns with selectors', () => {
    const cs = toRequestPattern({ ...newPattern('clients_to_servers'), servers: ['a'], bitrate: ' 5M ' });
    expect(cs).toMatchObject({ kind: 'clients_to_servers', servers: ['a'], clients: { roles: ['host'] }, bitrate: '5M' });
    const mesh = toRequestPattern({ ...newPattern('mesh'), nodeSet: 'pick', nodes: ['a', 'b'] });
    expect(mesh).toMatchObject({ kind: 'mesh', nodes: ['a', 'b'] });
    expect(mesh).not.toHaveProperty('servers');
  });

  it('explain what stops a draft', () => {
    const cs = newPattern('clients_to_servers');
    expect(patternError(cs, 0, 2000)).toBe('Pick at least one server');
    expect(patternError({ ...cs, servers: ['a'], bitrate: 'fast' }, 3, 2000)).toMatch(/Bitrate/);
    expect(patternError({ ...cs, servers: ['a'] }, 3000, 2000)).toBe('3000 flows; the server allows 2000');
    expect(patternError({ ...cs, servers: ['a'] }, 3, 2000)).toBeNull();
  });
});
