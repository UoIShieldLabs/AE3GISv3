import { beforeAll, describe, expect, it } from 'vitest';
import { applyCatalog, type Catalog, type NodeTypeSpec } from '@/catalog/catalog';
import { deviceLevel, deviceLevelInfo, deviceOwnLevel, inferSubnetLevel, subnetLevel } from '@/lib/purdue';
import type { Container, Position, Subnet, TopologyData } from '@/types/topology';
import { CATALOG } from '@/test/catalogFixture';
import { NODE_SIZE } from '../../constants';
import { layoutScope } from '../scope';

const type = (role: NodeTypeSpec['role'], purdueLevel?: number): NodeTypeSpec => ({
  displayName: role, role, category: 'misc', defaultImage: 'kathara/base', color: '#999', label: 'X', icon: 'default', description: '',
  ...(purdueLevel === undefined ? {} : { purdueLevel }),
});

// Levels as in the built-in catalog: none on switches, routers, attackers, IDSs.
const PURDUE_CATALOG: Catalog = {
  ...CATALOG,
  images: {
    ...CATALOG.images,
    // A workstation variant labelled io.ae3gis.purdue-level=0.
    'lab/process-sim:latest': { displayName: 'Process sim', description: '', stability: 'stable', purdueLevel: 0 },
  },
  types: {
    ...CATALOG.types,
    firewall: { ...CATALOG.types.firewall, purdueLevel: 3.5 },
    router: { ...CATALOG.types.router },
    switch: type('switch'),
    workstation: { ...type('host', 4), images: ['kathara/base', 'lab/process-sim:latest'] },
    'database-server': type('host', 4),
    'web-server': type('host', 4),
    attacker: type('host'),
    ids: type('host'),
    hmi: type('host', 2),
    plc: type('host', 1),
  },
};

beforeAll(() => applyCatalog(PURDUE_CATALOG));

const dev = (id: string, t: string, legs: string[] = [], image?: string): Container => ({
  id, name: id, type: t, ip: '10.0.0.1', ...(image ? { image } : {}),
  ...(legs.length ? { interfaces: legs.map((subnetId) => ({ subnetId, ip: '10.0.9.1' })) } : {}),
});

const star = (sw: string, ids: string[]) => ids.map((id) => ({ id: `${sw}-${id}`, from: sw, to: id }));

const subnet = (id: string, containers: Container[], extra: Partial<Subnet> = {}): Subnet => ({
  id, name: id, cidr: '10.0.0.0/24', containers, connections: [], ...extra,
});

const siteOf = (subnets: Subnet[]): TopologyData => ({
  sites: [{ id: 's', name: 'Lab', location: '', position: { x: 0, y: 0 }, subnets, subnetConnections: [] }], siteConnections: [],
});

/** The ICS preset's shape: IT-LAN bridged to OT-LAN by fw + historian, OT-LAN
 *  to PROCESS by the plc; process-sim's image is labelled L0. */
function ics(): TopologyData {
  return siteOf([
    subnet('it', [dev('fw', 'firewall', ['ot']), dev('it-sw', 'switch'), dev('attacker', 'attacker'), dev('engws', 'workstation'), dev('historian', 'database-server', ['ot'])], {
      name: 'IT-LAN', connections: star('it-sw', ['fw', 'attacker', 'historian', 'engws']),
    }),
    subnet('ot', [dev('ot-sw', 'switch'), dev('plc', 'plc', ['process']), dev('hmi', 'hmi'), dev('ids', 'ids')], {
      name: 'OT-LAN', connections: star('ot-sw', ['plc', 'hmi', 'ids']),
    }),
    subnet('process', [dev('proc-sw', 'switch'), dev('process-sim', 'workstation', [], 'lab/process-sim:latest')], {
      name: 'PROCESS', connections: star('proc-sw', ['process-sim']),
    }),
  ]);
}

const site = { level: 'site', siteId: 's' } as const;
const W = NODE_SIZE.device.width;
const centre = (p: Position) => p.x + W / 2;
/** Device ids per row, top to bottom, each row left to right. */
function rowsOf(pos: Map<string, Position>, ids: string[]): string[][] {
  const ys = [...new Set(ids.map((id) => pos.get(id)!.y))].sort((a, b) => a - b);
  return ys.map((y) => ids.filter((id) => pos.get(id)!.y === y).sort((a, b) => pos.get(a)!.x - pos.get(b)!.x));
}
const idsOf = (t: TopologyData, subnetId: string) => t.sites[0].subnets.find((s) => s.id === subnetId)!.containers.map((c) => c.id);

describe('Purdue levels', () => {
  it("takes a device's image level over its type's, else its subnet's", () => {
    const [it, , proc] = ics().sites[0].subnets;
    expect(deviceOwnLevel(dev('w', 'workstation'))).toBe(4);
    expect(deviceOwnLevel(dev('sim', 'workstation', [], 'lab/process-sim:latest'))).toBe(0);
    expect(deviceLevelInfo(dev('sim', 'workstation', [], 'lab/process-sim:latest'), proc)).toEqual({ level: 0, source: 'image' });
    // Switches and attackers have no level of their own: their subnet's.
    expect(deviceOwnLevel(dev('sw', 'switch'))).toBeUndefined();
    expect(deviceLevelInfo(dev('sw', 'switch'), proc)).toEqual({ level: 0, source: 'subnet' });
    expect(deviceLevel(dev('a', 'attacker'), it)).toBe(4);
  });

  it('infers a subnet from the hosts that have a level of their own', () => {
    const [it, ot, proc] = ics().sites[0].subnets;
    expect(inferSubnetLevel(it)).toBe(4);
    expect(inferSubnetLevel(ot)).toBe(2);
    expect(inferSubnetLevel(proc)).toBe(0);
    expect(inferSubnetLevel({ name: 'x', containers: [dev('a', 'attacker'), dev('i', 'ids')] })).toBe(4);
  });

  it('reads "DMZ" in the name, defaults to L4, and an override wins', () => {
    expect(inferSubnetLevel({ name: 'Corp DMZ', containers: [dev('web', 'web-server')] })).toBe(3.5);
    expect(inferSubnetLevel({ name: 'empty', containers: [dev('sw', 'switch')] })).toBe(4);
    expect(subnetLevel({ name: 'x', containers: [dev('w', 'workstation')], purdueLevel: 0 })).toBe(0);
    expect(subnetLevel({ name: 'x', containers: [], purdueLevel: 3.4 })).toBe(3.5);
  });
});

describe('Purdue layout', () => {
  it('stacks subnets by level, each row centred', () => {
    const pos = layoutScope(ics(), site, 'purdue');
    const [it, ot, proc] = ['it', 'ot', 'process'].map((id) => pos.get(id)!);
    expect(it.y).toBeLessThan(ot.y);
    expect(ot.y).toBeLessThan(proc.y);
    for (const p of [it, ot, proc]) expect(p.x).toBe(-NODE_SIZE.subnet.width / 2);
  });

  it('puts subnets of one level side by side, ordered under their neighbours', () => {
    const t = ics();
    const s = t.sites[0];
    // A second IT subnet, and a second OT one hanging off it, listed first.
    s.subnets.unshift(subnet('ot2', [dev('hmi2', 'hmi')]));
    s.subnets.push(subnet('it2', [dev('ws2', 'workstation', ['ot2'])]));
    const p = layoutScope(t, site, 'purdue');
    expect(p.get('it')!.y).toBe(p.get('it2')!.y);
    expect(p.get('it')!.x).toBeLessThan(p.get('it2')!.x);
    expect(p.get('it')!.x + p.get('it2')!.x + NODE_SIZE.subnet.width).toBeCloseTo(0);
    // ot2 hangs off it2 (right), ot off it (left): reordered despite input order.
    expect(p.get('ot')!.y).toBe(p.get('ot2')!.y);
    expect(p.get('ot')!.x).toBeLessThan(p.get('ot2')!.x);
  });

  it('puts the switch on the edge bordering the next zone, bridging devices past it', () => {
    const t = ics();
    const pos = layoutScope(t, site, 'purdue');
    // IT: switch at the bottom of the office rows; fw and historian bridge down below it.
    expect(rowsOf(pos, idsOf(t, 'it'))).toEqual([['attacker', 'engws'], ['it-sw'], ['fw', 'historian']]);
    // OT: switch on top; the plc bridges down to PROCESS.
    expect(rowsOf(pos, idsOf(t, 'ot'))).toEqual([['ot-sw'], ['hmi', 'ids'], ['plc']]);
    expect(rowsOf(pos, idsOf(t, 'process'))).toEqual([['proc-sw'], ['process-sim']]);
    for (const row of [['attacker', 'engws'], ['fw', 'historian'], ['it-sw'], ['plc']]) {
      expect(row.reduce((s, id) => s + centre(pos.get(id)!), 0) / row.length).toBeCloseTo(0);
    }
  });

  it('puts a lower-level device under the IT switch and a higher-level one over the OT switch', () => {
    const t = siteOf([
      subnet('it', [dev('sw', 'switch'), dev('ws', 'workstation'), dev('fw', 'firewall')]),
      subnet('ot', [dev('ot-sw', 'switch'), dev('plc', 'plc'), dev('ws2', 'workstation')]),
    ]);
    const pos = layoutScope(t, site, 'purdue');
    expect(rowsOf(pos, ['sw', 'ws', 'fw'])).toEqual([['ws'], ['sw'], ['fw']]);
    // A workstation (L4) in an L1 subnet: over the OT switch.
    expect(rowsOf(pos, ['ot-sw', 'plc', 'ws2'])).toEqual([['ws2'], ['ot-sw'], ['plc']]);
  });

  it('lays out a DMZ: IT-side router on top, OT-side router at the bottom, switches around its own row', () => {
    const dmz = (switches: string[]) => siteOf([
      subnet('it', [dev('ws', 'workstation')]),
      subnet('dmz', [...switches.map((id) => dev(id, 'switch')), dev('fw', 'firewall'), dev('ids', 'ids'), dev('r-it', 'router', ['it']), dev('r-ot', 'router', ['ot'])], { name: 'DMZ' }),
      subnet('ot', [dev('plc', 'plc')]),
    ]);
    const one = layoutScope(dmz(['sw']), site, 'purdue');
    expect(rowsOf(one, ['sw', 'fw', 'ids', 'r-it', 'r-ot'])).toEqual([['r-it'], ['sw'], ['fw', 'ids'], ['r-ot']]);
    const two = layoutScope(dmz(['sw-a', 'sw-b']), site, 'purdue');
    expect(rowsOf(two, ['sw-a', 'sw-b', 'fw', 'ids', 'r-it', 'r-ot'])).toEqual([['r-it'], ['sw-a'], ['fw', 'ids'], ['sw-b'], ['r-ot']]);
  });

  it('sizes expanded subnets from their new device layout', () => {
    const collapsed = layoutScope(ics(), site, 'purdue');
    const expanded = layoutScope(ics(), site, 'purdue', { expanded: { it: true } });
    // IT-LAN grows to 3 device rows, pushing the rows below it down.
    expect(expanded.get('ot')!.y).toBeGreaterThan(collapsed.get('ot')!.y);
    expect(expanded.get('it')!.x).toBeLessThan(collapsed.get('it')!.x);
  });

  it('in a LAN view, reads which edge to use from the stored subnet positions', () => {
    const t = ics();
    t.sites[0].subnets.forEach((s, i) => { s.position = { x: 0, y: i * 300 }; });
    const pos = layoutScope(t, { level: 'subnet', siteId: 's', subnetId: 'ot' }, 'purdue');
    expect([...pos.keys()].sort()).toEqual(['hmi', 'ids', 'ot-sw', 'plc']);
    expect(rowsOf(pos, idsOf(t, 'ot'))).toEqual([['ot-sw'], ['hmi', 'ids'], ['plc']]);
    // PROCESS moved above OT-LAN: the plc now sits on the top edge.
    t.sites[0].subnets[2].position = { x: 0, y: -300 };
    const moved = layoutScope(t, { level: 'subnet', siteId: 's', subnetId: 'ot' }, 'purdue');
    expect(rowsOf(moved, idsOf(t, 'ot'))).toEqual([['plc'], ['ot-sw'], ['hmi', 'ids']]);
  });

  it('puts a device bridging to a subnet beside it at that end of its row', () => {
    const t = siteOf([
      subnet('it', [dev('it-sw', 'switch'), dev('a', 'workstation'), dev('b', 'workstation', ['side']), dev('c', 'workstation')]),
      subnet('side', [dev('ws3', 'workstation')]),
    ]);
    const pos = layoutScope(t, site, 'purdue');
    expect(pos.get('it')!.y).toBe(pos.get('side')!.y);
    expect(rowsOf(pos, ['it-sw', 'a', 'b', 'c'])).toEqual([['a', 'c', 'b'], ['it-sw']]);
  });

  it('falls back to the tree layout at root scope', () => {
    const t = ics();
    expect(layoutScope(t, { level: 'root' }, 'purdue')).toEqual(layoutScope(t, { level: 'root' }, 'tree'));
  });
});
