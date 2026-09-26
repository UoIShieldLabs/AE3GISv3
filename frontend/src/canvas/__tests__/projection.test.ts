import { describe, it, expect } from 'vitest';
import { activityIndex, project, toStoredPosition } from '../projection';
import type { TopologyData } from '@/types/topology';

function fixture(): TopologyData {
  return {
    sites: [
      {
        id: 'site-a', name: 'A', location: 'x', position: { x: 0, y: 0 },
        subnets: [
          {
            id: 'sub-1', name: 'S1', cidr: '10.0.1.0/24', gateway: '10.0.1.1', position: { x: 100, y: 100 },
            containers: [
              { id: 'r1', name: 'R1', type: 'router', ip: '10.0.1.1', position: { x: 10, y: 10 } },
              { id: 'sw1', name: 'SW1', type: 'switch', ip: '10.0.1.2', position: { x: 10, y: 120 } },
              { id: 'h1', name: 'H1', type: 'workstation', ip: '10.0.1.5', position: { x: 200, y: 120 } },
            ],
            connections: [
              { id: 'c-up', from: 'sw1', to: 'r1' },
              { id: 'c-h', from: 'sw1', to: 'h1' },
            ],
          },
          {
            id: 'sub-2', name: 'S2', cidr: '10.0.2.0/24', gateway: '10.0.2.1', position: { x: 500, y: 100 },
            containers: [{ id: 'r2', name: 'R2', type: 'router', ip: '10.0.2.1', position: { x: 0, y: 0 } }],
            connections: [],
          },
        ],
        subnetConnections: [{ id: 'c-wan', from: 'sub-1', to: 'sub-2', fromContainer: 'r1', toContainer: 'r2' }],
      },
      { id: 'site-b', name: 'B', location: 'y', position: { x: 800, y: 0 }, subnets: [], subnetConnections: [] },
    ],
    siteConnections: [{ id: 'c-site', from: 'site-a', to: 'site-b', fromContainer: 'r1' }],
  };
}

describe('project()', () => {
  it('root scope: one node per site, site edges between them', () => {
    const { nodes, edges } = project({ topology: fixture(), scope: { level: 'root' }, expanded: {} });
    expect(nodes.map((n) => n.type)).toEqual(['site', 'site']);
    expect(edges).toHaveLength(1);
    expect(edges[0]).toMatchObject({ id: 'c-site', source: 'site-a', target: 'site-b', data: { variant: 'site' } });
  });

  it('site scope: subnets and the inter-subnet edge', () => {
    const { nodes, edges } = project({ topology: fixture(), scope: { level: 'site', siteId: 'site-a' }, expanded: {} });
    expect(nodes.map((n) => n.id)).toEqual(['sub-1', 'sub-2']);
    expect(edges).toEqual([expect.objectContaining({ id: 'c-wan', source: 'sub-1', target: 'sub-2' })]);
  });

  it('subnet scope: devices with link/uplink variants and stable ids', () => {
    const { nodes, edges } = project({ topology: fixture(), scope: { level: 'subnet', siteId: 'site-a', subnetId: 'sub-1' }, expanded: {} });
    expect(nodes.map((n) => n.id)).toEqual(['r1', 'sw1', 'h1']);
    expect(edges.find((e) => e.id === 'c-up')?.data?.variant).toBe('uplink');
    expect(edges.find((e) => e.id === 'c-h')?.data?.variant).toBe('link');
    expect(nodes.find((n) => n.id === 'r1')?.data).toMatchObject({ isGateway: true, role: 'router' });
  });

  it('expanded subnet in site scope: group + relative children, edge re-targets to routers', () => {
    const { nodes, edges } = project({ topology: fixture(), scope: { level: 'site', siteId: 'site-a' }, expanded: { 'sub-1': true, 'sub-2': true } });
    const group = nodes.find((n) => n.id === 'sub-1');
    expect(group?.type).toBe('group');
    const r1 = nodes.find((n) => n.id === 'r1')!;
    expect(r1.parentId).toBe('sub-1');
    // children are rendered relative to the group's origin and land inside the header/padding
    expect(r1.position.x).toBeGreaterThan(0);
    expect(r1.position.y).toBeGreaterThan(0);
    const wan = edges.find((e) => e.id === 'c-wan')!;
    expect(wan.source).toBe('r1');
    expect(wan.target).toBe('r2');
    // round-trip: rendered position + origin == stored
    expect(toStoredPosition(r1, nodes)).toEqual({ x: 10, y: 10 });
  });

  it('one expanded, one collapsed: edge goes router → subnet node', () => {
    const { edges } = project({ topology: fixture(), scope: { level: 'site', siteId: 'site-a' }, expanded: { 'sub-1': true } });
    const wan = edges.find((e) => e.id === 'c-wan')!;
    expect(wan.source).toBe('r1');
    expect(wan.target).toBe('sub-2');
  });

  it('expanded site at root: nested groups and site edge anchored on the visible endpoint', () => {
    const { nodes, edges } = project({ topology: fixture(), scope: { level: 'root' }, expanded: { 'site-a': true, 'sub-1': true } });
    expect(nodes.find((n) => n.id === 'site-a')?.type).toBe('group');
    expect(nodes.find((n) => n.id === 'sub-1')).toMatchObject({ type: 'group', parentId: 'site-a' });
    expect(nodes.find((n) => n.id === 'r1')).toMatchObject({ parentId: 'sub-1' });
    const siteEdge = edges.find((e) => e.id === 'c-site')!;
    expect(siteEdge.source).toBe('r1');
    expect(siteEdge.target).toBe('site-b');
  });

  it('expanded subnet without explicit endpoint containers anchors on the gateway router', () => {
    const t = fixture();
    t.sites[0].subnetConnections = [{ id: 'c-wan', from: 'sub-1', to: 'sub-2' }];
    const { edges } = project({ topology: t, scope: { level: 'site', siteId: 'site-a' }, expanded: { 'sub-1': true } });
    expect(edges.find((e) => e.id === 'c-wan')).toMatchObject({ source: 'r1', target: 'sub-2' });
  });

  it('marks selection and runtime status', () => {
    const { nodes, edges } = project({
      topology: fixture(),
      scope: { level: 'subnet', siteId: 'site-a', subnetId: 'sub-1' },
      expanded: {},
      containerStatus: { r1: 'running', sw1: 'running' },
      selection: { nodeIds: ['h1'], edgeIds: ['c-up'] },
    });
    expect(nodes.find((n) => n.id === 'h1')?.selected).toBe(true);
    expect(nodes.find((n) => n.id === 'r1')?.selected).toBe(false);
    expect(edges.find((e) => e.id === 'c-up')).toMatchObject({ selected: true, data: { active: true } });
    expect(edges.find((e) => e.id === 'c-h')?.data?.active).toBe(false);
  });
});

describe('project() — runtime activity', () => {
  const activity = activityIndex([
    { job_id: 'cap1', kind: 'capture', status: 'running', label: '', node_ids: ['r1', 'r2'], connection_ids: ['c-wan'] },
    { job_id: 'run1', kind: 'traffic', status: 'running', label: '', node_ids: ['h1', 'r2'], connection_ids: [] },
  ]);

  it('badges the captured link and the capturing node, and traffic endpoints', () => {
    const { nodes, edges } = project({ topology: fixture(), scope: { level: 'site', siteId: 'site-a' }, expanded: { 'sub-1': true, 'sub-2': true }, activity });
    // The subnet link is drawn between the expanded gateways and still carries the capture.
    const wan = edges.find((e) => e.id === 'c-wan')!;
    expect(wan).toMatchObject({ source: 'r1', target: 'r2', data: { captureJobId: 'cap1' } });
    expect(edges.find((e) => e.id === 'c-h')!.data!.captureJobId).toBeUndefined();
    const device = (id: string) => nodes.find((n) => n.id === id)!.data as Record<string, unknown>;
    expect(device('r1').captureJobId).toBe('cap1');
    expect(device('r2').captureJobId).toBeUndefined(); // the peer, not where the sidecar runs
    expect(device('h1').traffic).toBe(true);
    expect(device('r2').traffic).toBe(true);
    expect(device('sw1').traffic).toBeUndefined();
  });

  it('collapsed subnets still carry the link badge', () => {
    const { edges } = project({ topology: fixture(), scope: { level: 'site', siteId: 'site-a' }, expanded: {}, activity });
    expect(edges[0]).toMatchObject({ id: 'c-wan', source: 'sub-1', target: 'sub-2', data: { captureJobId: 'cap1' } });
  });
});
