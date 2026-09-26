import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore, undo, redo, clearHistory } from '../index';
import { findSite, findSubnet, locate, locateConnection } from '@/lib/topology';

const store = useAppStore;
const S = () => store.getState();

beforeEach(() => {
  S().newTopology('Test');
  clearHistory();
});

describe('topology store — sites/subnets/containers', () => {
  it('addSite adds a positioned site and marks dirty', () => {
    const id = S().addSite({ name: 'HQ', location: 'Berlin' });
    const site = findSite(S().topology, id)!;
    expect(site.name).toBe('HQ');
    expect(site.position).toBeDefined();
    expect(S().dirty).toBe(true);
  });

  it('addSubnet auto-creates a router + switch wired together with positions', () => {
    const siteId = S().addSite({ name: 'S1' });
    const subnetId = S().addSubnet({ siteId, name: 'LAN', cidr: '10.0.1.0/24' })!;
    const subnet = findSubnet(S().topology, siteId, subnetId)!;
    expect(subnet.containers.map((c) => c.type)).toEqual(['router', 'switch']);
    expect(subnet.containers[0].ip).toBe('10.0.1.1');
    expect(subnet.containers[1].ip).toBe('10.0.1.2');
    expect(subnet.gateway).toBe('10.0.1.1');
    expect(subnet.connections).toHaveLength(1);
    expect(subnet.connections[0].id).toBeTruthy();
    expect(subnet.containers.every((c) => c.position)).toBe(true);
  });

  it('addContainer assigns the next free IP and an auto name', () => {
    const siteId = S().addSite({ name: 'S1' });
    const subnetId = S().addSubnet({ siteId, name: 'LAN', cidr: '10.0.1.0/24' })!;
    const id = S().addContainer({ subnetId, type: 'workstation' })!;
    const hit = locate(S().topology, id);
    expect(hit?.kind).toBe('container');
    if (hit?.kind !== 'container') return;
    expect(hit.container.ip).toBe('10.0.1.3');
    expect(hit.container.name).toMatch(/1$/);
  });

  it('deleteNodes removes a container and its connections', () => {
    const siteId = S().addSite({ name: 'S1' });
    const subnetId = S().addSubnet({ siteId, name: 'LAN', cidr: '10.0.1.0/24' })!;
    const ws = S().addContainer({ subnetId, type: 'workstation' })!;
    const sw = findSubnet(S().topology, siteId, subnetId)!.containers[1].id;
    const cid = S().addConnection({ from: sw, to: ws })!;
    expect(locateConnection(S().topology, cid)).not.toBeNull();
    S().deleteNodes([ws]);
    expect(locate(S().topology, ws)).toBeNull();
    expect(locateConnection(S().topology, cid)).toBeNull();
  });

  it('deleteNodes on a site drops its site connections', () => {
    const a = S().addSite({ name: 'A' });
    const b = S().addSite({ name: 'B' });
    S().addConnection({ from: a, to: b });
    expect(S().topology.siteConnections).toHaveLength(1);
    S().deleteNodes([a]);
    expect(S().topology.sites).toHaveLength(1);
    expect(S().topology.siteConnections).toHaveLength(0);
  });

  it('duplicateNodes copies a container with a fresh id, name and ip', () => {
    const siteId = S().addSite({ name: 'S1' });
    const subnetId = S().addSubnet({ siteId, name: 'LAN', cidr: '10.0.1.0/24' })!;
    const ws = S().addContainer({ subnetId, type: 'workstation', name: 'Host 1' })!;
    const [copy] = S().duplicateNodes([ws]);
    const hit = locate(S().topology, copy);
    expect(hit?.kind).toBe('container');
    if (hit?.kind !== 'container') return;
    expect(hit.container.name).toBe('Host 2');
    expect(hit.container.ip).toBe('10.0.1.4');
    expect(copy).not.toBe(ws);
  });
});

describe('topology store — connections', () => {
  it('links two subnets in a site via their routers (auto-creating the router when missing)', () => {
    const siteId = S().addSite({ name: 'S1' });
    const a = S().addSubnet({ siteId, name: 'A', cidr: '10.0.1.0/24' })!;
    const b = S().addSubnet({ siteId, name: 'B', cidr: '10.0.2.0/24', autoInfra: false })!;
    const id = S().addConnection({ from: a, to: b })!;
    const site = findSite(S().topology, siteId)!;
    const conn = site.subnetConnections.find((c) => c.id === id)!;
    expect(conn.from).toBe(a);
    expect(conn.to).toBe(b);
    expect(conn.fromContainer).toBeTruthy();
    expect(conn.toContainer).toBeTruthy();
    const bSubnet = findSubnet(S().topology, siteId, b)!;
    expect(bSubnet.containers.some((c) => c.type === 'router')).toBe(true);
    expect(bSubnet.gateway).toBe('10.0.2.1');
  });

  it('rejects duplicate links in either direction', () => {
    const siteId = S().addSite({ name: 'S1' });
    const a = S().addSubnet({ siteId, name: 'A', cidr: '10.0.1.0/24' })!;
    const b = S().addSubnet({ siteId, name: 'B', cidr: '10.0.2.0/24' })!;
    expect(S().addConnection({ from: a, to: b })).not.toBeNull();
    expect(S().addConnection({ from: b, to: a })).toBeNull();
  });

  it('router ↔ router across subnets becomes an inter-subnet link; hosts cannot cross subnets', () => {
    const siteId = S().addSite({ name: 'S1' });
    const a = S().addSubnet({ siteId, name: 'A', cidr: '10.0.1.0/24' })!;
    const b = S().addSubnet({ siteId, name: 'B', cidr: '10.0.2.0/24' })!;
    const ra = findSubnet(S().topology, siteId, a)!.containers[0].id;
    const rb = findSubnet(S().topology, siteId, b)!.containers[0].id;
    const id = S().addConnection({ from: ra, to: rb })!;
    const conn = findSite(S().topology, siteId)!.subnetConnections.find((c) => c.id === id)!;
    expect(conn.fromContainer).toBe(ra);
    expect(conn.toContainer).toBe(rb);
    const host = S().addContainer({ subnetId: a, type: 'workstation' })!;
    expect(S().addConnection({ from: host, to: rb })).toBeNull();
  });

  it('site ↔ site links anchor on each site router', () => {
    const a = S().addSite({ name: 'A' });
    const b = S().addSite({ name: 'B' });
    S().addSubnet({ siteId: a, name: 'A1', cidr: '10.0.1.0/24' });
    S().addSubnet({ siteId: b, name: 'B1', cidr: '10.0.2.0/24' });
    const id = S().addConnection({ from: a, to: b, label: 'WAN' })!;
    const conn = S().topology.siteConnections.find((c) => c.id === id)!;
    expect(conn.label).toBe('WAN');
    expect(conn.fromContainer).toBeTruthy();
    expect(conn.toContainer).toBeTruthy();
  });
});

describe('topology store — load, dirty, undo', () => {
  it('loadTopology normalises ids/positions and preserves unknown fields', () => {
    S().loadTopology({
      name: 'X',
      sites: [{ id: 's1', name: 'S', location: '', position: { x: 10, y: 10 }, subnets: [
        { id: 'n1', name: 'N', cidr: '10.0.0.0/24', containers: [{ id: 'c1', name: 'C', type: 'workstation', ip: '10.0.0.5', extra: 'keep' }], connections: [{ from: 'c1', to: 'c1' }] },
      ], subnetConnections: [] }],
      siteConnections: [],
      customTopLevel: { a: 1 },
    });
    const t = S().topology;
    // The connection had no id: it got one, which has to be saved.
    expect(S().dirty).toBe(true);
    expect(t.customTopLevel).toEqual({ a: 1 });
    expect(t.sites[0].subnets[0].containers[0].extra).toBe('keep');
    expect(t.sites[0].subnets[0].containers[0].position).toBeDefined();
    expect(t.sites[0].subnets[0].position).toBeDefined();
    expect(t.sites[0].subnets[0].connections[0].id).toBeTruthy();
    // v1 site positions are rescaled once
    expect(t.sites[0].position).toEqual({ x: 30, y: 25 });
    expect(t.view?.version).toBe(2);
  });

  it('undo/redo restore topology and recompute dirty against the saved snapshot', () => {
    S().addSite({ name: 'A' });
    S().markClean();
    expect(S().dirty).toBe(false);
    S().addSite({ name: 'B' });
    expect(S().topology.sites).toHaveLength(2);
    expect(S().dirty).toBe(true);
    undo();
    expect(S().topology.sites).toHaveLength(1);
    expect(S().dirty).toBe(false);
    redo();
    expect(S().topology.sites).toHaveLength(2);
    expect(S().dirty).toBe(true);
  });

  it('moveNodes updates positions for any entity kind', () => {
    const siteId = S().addSite({ name: 'S1' });
    const subnetId = S().addSubnet({ siteId, name: 'LAN', cidr: '10.0.1.0/24' })!;
    const c = findSubnet(S().topology, siteId, subnetId)!.containers[0].id;
    S().moveNodes([{ id: siteId, position: { x: 1, y: 2 } }, { id: subnetId, position: { x: 3, y: 4 } }, { id: c, position: { x: 5, y: 6 } }]);
    expect(findSite(S().topology, siteId)!.position).toEqual({ x: 1, y: 2 });
    expect(findSubnet(S().topology, siteId, subnetId)!.position).toEqual({ x: 3, y: 4 });
    const hit = locate(S().topology, c);
    expect(hit?.kind === 'container' && hit.container.position).toEqual({ x: 5, y: 6 });
  });

  it('applyLayout positions every child of a scope', () => {
    const siteId = S().addSite({ name: 'S1' });
    const subnetId = S().addSubnet({ siteId, name: 'LAN', cidr: '10.0.1.0/24' })!;
    S().addContainer({ subnetId, type: 'workstation' });
    S().addContainer({ subnetId, type: 'workstation' });
    S().applyLayout({ level: 'subnet', siteId, subnetId }, 'grid');
    const positions = findSubnet(S().topology, siteId, subnetId)!.containers.map((c) => `${c.position!.x},${c.position!.y}`);
    expect(new Set(positions).size).toBe(positions.length);
  });
});

describe('document / runtime status', () => {
  it('keeps container runtime status out of the topology data', () => {
    const siteId = S().addSite({ name: 'S1' });
    const subnetId = S().addSubnet({ siteId, name: 'LAN', cidr: '10.0.1.0/24' })!;
    const c = findSubnet(S().topology, siteId, subnetId)!.containers[0].id;
    const before = S().dirty;
    S().setContainerStatuses({ [c]: 'running' });
    expect(S().containerStatus[c]).toBe('running');
    expect(S().dirty).toBe(before);
    const hit = locate(S().topology, c);
    expect(hit?.kind === 'container' && hit.container.status).toBeUndefined();
  });
});

describe('topology store — loading', () => {
  const data = {
    name: 'T',
    sites: [{ id: 's', name: 'S', location: '', subnets: [{ id: 'n', name: 'N', cidr: '10.0.0.0/24', containers: [], connections: [{ from: 'a', to: 'b' }] }], subnetConnections: [] }],
    siteConnections: [],
  };

  it('a load that had to invent connection ids starts dirty (they must be saved)', () => {
    S().loadTopology(data);
    expect(S().dirty).toBe(true);
    expect(S().topology.sites[0].subnets[0].connections[0].id).toBeTruthy();
  });

  it('a load with ids already in place is clean', () => {
    const withIds = JSON.parse(JSON.stringify(data));
    withIds.sites[0].subnets[0].connections[0].id = 'c1';
    S().loadTopology(withIds);
    expect(S().dirty).toBe(false);
  });

  it('saved traffic flows are part of the design (undoable, dirty)', () => {
    S().setTrafficFlows([{ id: 'f1', client: 'a', server: 'b', protocol: 'tcp', direction: 'forward' }]);
    expect(S().topology.traffic?.flows?.[0].id).toBe('f1');
    expect(S().dirty).toBe(true);
    undo();
    expect(S().topology.traffic?.flows).toBeUndefined();
  });
});
