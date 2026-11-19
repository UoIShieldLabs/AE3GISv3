import { describe, it, expect } from 'vitest';
import { currentLayout, layoutFootprint } from '../applied';
import { normalizeTopology } from '@/store/normalize';
import type { TopologyData } from '@/types/topology';

const topo = (): TopologyData => ({
  sites: [{
    id: 's1', name: 'S1', location: '', position: { x: 0, y: 0 }, subnetConnections: [],
    subnets: [{
      id: 'n1', name: 'LAN', cidr: '10.0.1.0/24', position: { x: 0, y: 0 }, connections: [],
      containers: [{ id: 'c1', name: 'c1', type: 'workstation', ip: '10.0.1.5', position: { x: 10, y: 10 } }],
    }],
  }],
  siteConnections: [],
});

describe('applied layout', () => {
  const site = { level: 'site', siteId: 's1' } as const;

  it('reads as custom without a record or with an unknown mode', () => {
    const t = topo();
    expect(currentLayout(t, site)).toBe('custom');
    t.sites[0].layout = { mode: 'spiral', footprint: layoutFootprint(t, site, 'tree') };
    expect(currentLayout(t, site)).toBe('custom');
  });

  it('a Purdue site layout also covers the devices it placed; Tree does not', () => {
    const t = topo();
    t.sites[0].layout = { mode: 'purdue', footprint: layoutFootprint(t, site, 'purdue') };
    const tree = layoutFootprint(t, site, 'tree');
    t.sites[0].subnets[0].containers[0].position = { x: 50, y: 10 };
    expect(currentLayout(t, site)).toBe('custom');
    expect(layoutFootprint(t, site, 'tree')).toBe(tree);
  });

  it('normalize records Tree for a scope it lays out from scratch', () => {
    const t = topo();
    delete t.sites[0].subnets[0].containers[0].position;
    const n = normalizeTopology(t);
    expect(currentLayout(n, { level: 'subnet', siteId: 's1', subnetId: 'n1' })).toBe('tree');
    expect(currentLayout(n, site)).toBe('custom');
  });
});
