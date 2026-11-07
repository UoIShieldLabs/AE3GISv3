import { beforeAll, describe, expect, it } from 'vitest';
import { applyCatalog, type Catalog, type NodeTypeSpec } from '@/catalog/catalog';
import { inferSubnetLevel, subnetLevel } from '@/lib/purdue';
import type { Container, Position, Subnet, TopologyData } from '@/types/topology';
import { CATALOG } from '@/test/catalogFixture';
import { NODE_SIZE } from '../../constants';
import { layoutScope } from '../scope';

const type = (role: NodeTypeSpec['role'], purdueLevel: number): NodeTypeSpec => ({
  displayName: role, role, category: 'misc', defaultImage: 'kathara/base', color: '#999', label: 'X', icon: 'default', description: '', purdueLevel,
});

const PURDUE_CATALOG: Catalog = {
  ...CATALOG,
  types: {
    ...CATALOG.types,
    firewall: { ...CATALOG.types.firewall, purdueLevel: 3.5 },
    router: { ...CATALOG.types.router, purdueLevel: 3 },
    switch: type('switch', 2),
    workstation: type('host', 4),
    'database-server': type('host', 4),
    'web-server': type('host', 4),
    attacker: type('host', 5),
    ids: type('host', 3.5),
    hmi: type('host', 2),
    plc: type('host', 1),
  },
};

beforeAll(() => applyCatalog(PURDUE_CATALOG));

const dev = (id: string, t: string, legs: string[] = []): Container => ({
  id, name: id, type: t, ip: '10.0.0.1', ...(legs.length ? { interfaces: legs.map((subnetId) => ({ subnetId, ip: '10.0.9.1' })) } : {}),
});

const star = (sw: string, ids: string[]) => ids.map((id) => ({ id: `${sw}-${id}`, from: sw, to: id }));

/** The ICS preset's shape: IT-LAN bridged to OT-LAN by fw + historian, OT-LAN to PROCESS by the plc. */
function ics(): TopologyData {
  const subnets: Subnet[] = [
    {
      id: 'it', name: 'IT-LAN', cidr: '10.0.5.0/24',
      containers: [dev('fw', 'firewall', ['ot']), dev('it-sw', 'switch'), dev('attacker', 'attacker'), dev('engws', 'workstation'), dev('historian', 'database-server', ['ot'])],
      connections: star('it-sw', ['fw', 'attacker', 'historian', 'engws']),
    },
    {
      id: 'ot', name: 'OT-LAN', cidr: '10.0.3.0/24',
      containers: [dev('ot-sw', 'switch'), dev('plc', 'plc', ['process']), dev('hmi', 'hmi'), dev('ids', 'ids')],
      connections: star('ot-sw', ['plc', 'hmi', 'ids']),
    },
    {
      id: 'process', name: 'PROCESS', cidr: '10.0.1.0/24', purdueLevel: 0,
      containers: [dev('proc-sw', 'switch'), dev('process-sim', 'workstation')],
      connections: star('proc-sw', ['process-sim']),
    },
  ];
  return { sites: [{ id: 's', name: 'ICS Lab', location: '', position: { x: 0, y: 0 }, subnets, subnetConnections: [] }], siteConnections: [] };
}

const site = { level: 'site', siteId: 's' } as const;
const W = NODE_SIZE.device.width;
const centre = (p: Position) => p.x + W / 2;
/** Device ids per row, top to bottom, each row left to right. */
function rowsOf(pos: Map<string, Position>, ids: string[]): string[][] {
  const ys = [...new Set(ids.map((id) => pos.get(id)!.y))].sort((a, b) => a - b);
  return ys.map((y) => ids.filter((id) => pos.get(id)!.y === y).sort((a, b) => pos.get(a)!.x - pos.get(b)!.x));
}

describe('subnet Purdue level', () => {
  it('is the median level of its hosts, ignoring switches and routers', () => {
    const [it, ot] = ics().sites[0].subnets;
    expect(inferSubnetLevel(it)).toBe(4);
    expect(inferSubnetLevel(ot)).toBe(2);
  });

  it('reads "DMZ" in the name, defaults to L4, and an override wins', () => {
    expect(inferSubnetLevel({ name: 'Corp DMZ', containers: [dev('web', 'web-server')] })).toBe(3.5);
    expect(inferSubnetLevel({ name: 'empty', containers: [dev('sw', 'switch')] })).toBe(4);
    expect(subnetLevel(ics().sites[0].subnets[2])).toBe(0);
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
    s.subnets.unshift({ id: 'ot2', name: 'OT2', cidr: '10.0.7.0/24', containers: [dev('hmi2', 'hmi')], connections: [] });
    s.subnets.push({ id: 'it2', name: 'IT2', cidr: '10.0.6.0/24', containers: [dev('ws2', 'workstation', ['ot2'])], connections: [] });
    const pos = layoutScope(t, site, 'purdue', {}).entries();
    const p = new Map(pos);
    expect(p.get('it')!.y).toBe(p.get('it2')!.y);
    expect(p.get('it')!.x).toBeLessThan(p.get('it2')!.x);
    expect(p.get('it')!.x + p.get('it2')!.x + NODE_SIZE.subnet.width).toBeCloseTo(0);
    // ot2 hangs off it2 (right), ot off it (left): reordered despite input order.
    expect(p.get('ot')!.y).toBe(p.get('ot2')!.y);
    expect(p.get('ot')!.x).toBeLessThan(p.get('ot2')!.x);
  });

  it('rows devices by level with the bridging ones on the facing edge and the switch in the middle', () => {
    const pos = layoutScope(ics(), site, 'purdue');
    // fw (L3.5) and historian (L4) bridge to OT-LAN below: bottom row, centred.
    expect(rowsOf(pos, ['fw', 'it-sw', 'attacker', 'engws', 'historian'])).toEqual([['attacker'], ['it-sw'], ['engws', 'fw', 'historian']]);
    // The plc bridges to PROCESS below.
    expect(rowsOf(pos, ['ot-sw', 'plc', 'hmi', 'ids'])).toEqual([['ids'], ['ot-sw'], ['hmi', 'plc']]);
    // PROCESS has one row and its leg arrives from above: switch on top.
    expect(rowsOf(pos, ['proc-sw', 'process-sim'])).toEqual([['proc-sw'], ['process-sim']]);
    for (const row of [['engws', 'fw', 'historian'], ['hmi', 'plc'], ['attacker'], ['it-sw']]) {
      expect(row.reduce((s, id) => s + centre(pos.get(id)!), 0) / row.length).toBeCloseTo(0);
    }
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
    expect(rowsOf(pos, ['ot-sw', 'plc', 'hmi', 'ids'])).toEqual([['ids'], ['ot-sw'], ['hmi', 'plc']]);
    // PROCESS moved above OT-LAN: the plc now sits on the top edge.
    t.sites[0].subnets[2].position = { x: 0, y: -300 };
    const moved = layoutScope(t, { level: 'subnet', siteId: 's', subnetId: 'ot' }, 'purdue');
    expect(rowsOf(moved, ['ot-sw', 'plc', 'hmi', 'ids'])).toEqual([['ids', 'plc'], ['ot-sw'], ['hmi']]);
  });

  it('puts a device bridging to a subnet beside it at that end of its row', () => {
    const t = ics();
    const [it] = t.sites[0].subnets;
    t.sites[0].subnets = [it, { id: 'side', name: 'Side', cidr: '10.0.8.0/24', containers: [dev('ws3', 'workstation')], connections: [] }];
    it.containers = [dev('it-sw', 'switch'), dev('a', 'workstation'), dev('b', 'workstation', ['side']), dev('c', 'workstation')];
    const pos = layoutScope(t, site, 'purdue');
    expect(pos.get('it')!.y).toBe(pos.get('side')!.y);
    expect(rowsOf(pos, ['it-sw', 'a', 'b', 'c'])).toEqual([['it-sw'], ['a', 'c', 'b']]);
  });

  it('falls back to the tree layout at root scope', () => {
    const t = ics();
    expect(layoutScope(t, { level: 'root' }, 'purdue')).toEqual(layoutScope(t, { level: 'root' }, 'tree'));
  });
});
