import type { AttackPhase, Connection, Container, Position, ScriptExecution, Site, Subnet, TopologyData, SavedFlow, Tutorial, TutorialCell } from '@/types/topology';
import { createEmptyTopology } from '@/types/topology';
import { generateId } from '@/lib/ids';
import { getNextAvailableIp } from '@/utils/validation';
import { displayNameFor } from '@/catalog/catalog';
import {
  canTakeInterfaceLegs, gatewayOf, hasConnection, isRouterType, locate, locateConnection, nextName, siteRouter, usedIpsInSubnet,
} from '@/lib/topology';
import { layoutScope, nextFreePosition, type Rect } from '@/canvas/layout';
import { NODE_SIZE } from '@/canvas/constants';
import { cloneTopology, normalizeTopology, type NormalizeReport } from '../normalize';
import type { SliceCreator, TopologySlice, TutorialCellPatch } from '../types';

const rects = (items: { position?: Position }[], size: { width: number; height: number }): Rect[] =>
  items.filter((i) => i.position).map((i) => ({ ...i.position!, ...size }));

/** Find or create the gateway router of a subnet; wires the switch → router uplink when creating. */
function ensureRouter(top: TopologyData, subnet: Subnet): string {
  const existing = gatewayOf(subnet);
  if (existing) return existing.id;
  const taken = usedIpsInSubnet(top, subnet.id);
  const ip = getNextAvailableIp(subnet.cidr, taken) ?? '';
  const id = generateId('node');
  subnet.containers.push({
    id,
    name: `${subnet.name} Router`,
    type: 'router',
    ip,
    position: nextFreePosition(rects(subnet.containers, NODE_SIZE.device), NODE_SIZE.device),
  });
  subnet.gateway = ip;
  const sw = subnet.containers.find((c) => c.type === 'switch');
  if (sw && !hasConnection(subnet.connections, sw.id, id)) subnet.connections.push({ id: generateId('c'), from: sw.id, to: id });
  return id;
}

function remapIds<T extends { id?: string }>(items: T[], map: Map<string, string>): T[] {
  return items.map((item) => {
    const copy = { ...item } as T & { from?: string; to?: string; fromContainer?: string; toContainer?: string };
    if (copy.id) copy.id = generateId('c');
    if (copy.from) copy.from = map.get(copy.from) ?? copy.from;
    if (copy.to) copy.to = map.get(copy.to) ?? copy.to;
    if (copy.fromContainer) copy.fromContainer = map.get(copy.fromContainer) ?? copy.fromContainer;
    if (copy.toContainer) copy.toContainer = map.get(copy.toContainer) ?? copy.toContainer;
    return copy;
  });
}

const OFFSET = 32;

/** A duplicated device must not reuse its original's leg addresses or SPAN wiring.
 *  A single copy keeps its legs on fresh addresses (still multi-homed); copies made
 *  with their whole subnet/site keep legs and mirrors that point inside the copy
 *  (remapped through `map`) and drop the ones that point outside it. */
function rehomeCopy(top: TopologyData, copy: Container, map?: Map<string, string>) {
  if (copy.interfaces) {
    if (!canTakeInterfaceLegs(copy.type)) delete copy.interfaces;
    else if (map) {
      copy.interfaces = copy.interfaces
        .filter((leg) => map.has(leg.subnetId))
        .map((leg) => ({ ...leg, subnetId: map.get(leg.subnetId)! }));
    } else {
      copy.interfaces = copy.interfaces.flatMap((leg) => {
        const target = locate(top, leg.subnetId);
        if (target?.kind !== 'subnet') return [];
        const ip = getNextAvailableIp(target.subnet.cidr, usedIpsInSubnet(top, leg.subnetId)) ?? '';
        return [{ ...leg, ip }];
      });
    }
    if (!copy.interfaces?.length) delete copy.interfaces;
  }
  if (copy.mirrorTo) {
    const target = map?.get(copy.mirrorTo);
    if (target) copy.mirrorTo = target;
    else delete copy.mirrorTo;
  }
}

function dropConnections(top: TopologyData, ids: string[]) {
  const drop = new Set(ids);
  top.siteConnections = top.siteConnections.filter((c) => !drop.has(c.id!));
  for (const site of top.sites) {
    site.subnetConnections = site.subnetConnections.filter((c) => !drop.has(c.id!));
    for (const subnet of site.subnets) subnet.connections = subnet.connections.filter((c) => !drop.has(c.id!));
  }
}

function dropNodes(top: TopologyData, ids: string[]) {
  const drop = new Set(ids);
  const touches = (c: Connection) => drop.has(c.from) || drop.has(c.to);
  const scrubRefs = (c: Connection) => {
    if (c.fromContainer && drop.has(c.fromContainer)) delete c.fromContainer;
    if (c.toContainer && drop.has(c.toContainer)) delete c.toContainer;
  };
  top.sites = top.sites.filter((site) => !drop.has(site.id));
  top.siteConnections = top.siteConnections.filter((c) => !touches(c));
  for (const site of top.sites) {
    site.subnets = site.subnets.filter((sn) => !drop.has(sn.id));
    site.subnetConnections = site.subnetConnections.filter((c) => !touches(c));
    for (const subnet of site.subnets) {
      subnet.containers = subnet.containers.filter((c) => !drop.has(c.id));
      subnet.connections = subnet.connections.filter((c) => !touches(c));
      if (subnet.gateway && !subnet.containers.some((c) => c.ip === subnet.gateway)) {
        const gw = gatewayOf(subnet);
        if (gw) subnet.gateway = gw.ip;
        else delete subnet.gateway;
      }
    }
    site.subnetConnections.forEach(scrubRefs);
  }
  top.siteConnections.forEach(scrubRefs);

  // Scrub multi-homing refs orphaned by the deletion: interface legs into a
  // subnet that no longer exists, and mirror targets that are gone.
  const liveSubnets = new Set<string>();
  const liveContainers = new Set<string>();
  for (const site of top.sites)
    for (const sn of site.subnets) {
      liveSubnets.add(sn.id);
      for (const c of sn.containers) liveContainers.add(c.id);
    }
  for (const site of top.sites)
    for (const sn of site.subnets)
      for (const c of sn.containers) {
        if (c.interfaces) {
          c.interfaces = c.interfaces.filter((leg) => liveSubnets.has(leg.subnetId));
          if (!c.interfaces.length) delete c.interfaces;
        }
        if (c.mirrorTo && !liveContainers.has(c.mirrorTo)) delete c.mirrorTo;
      }

  // Scrub scenario steps that ran on a node that no longer exists.
  if (Array.isArray(top.scenarios))
    for (const scenario of top.scenarios)
      for (const phase of scenario.phases ?? [])
        phase.executions = (phase.executions ?? []).filter((e) => liveContainers.has(e.containerId));
}

function findTutorial(top: TopologyData, tutorialId: string): Tutorial | undefined {
  return top.tutorials?.find((t) => t.id === tutorialId);
}

/** A new cell of `kind`, taking only the fields that kind has. */
function makeCell(kind: TutorialCell['kind'], init: TutorialCellPatch = {}): TutorialCell {
  const id = generateId('cell');
  return kind === 'markdown'
    ? { id, kind, source: init.source ?? '' }
    : { id, kind, containerId: init.containerId ?? '', command: init.command ?? '' };
}

function findPhase(top: TopologyData, phaseId: string): AttackPhase | undefined {
  for (const s of top.scenarios ?? []) {
    const p = s.phases?.find((ph) => ph.id === phaseId);
    if (p) return p;
  }
  return undefined;
}

export const createTopologySlice: SliceCreator<TopologySlice> = (set, get) => ({
  topology: normalizeTopology(createEmptyTopology()),
  dirty: false,
  savedTopology: null,

  loadTopology: (data) =>
    set((s) => {
      const report: NormalizeReport = { filledConnectionIds: 0 };
      const t = normalizeTopology(cloneTopology(data as TopologyData), report);
      s.topology = t;
      // Connections are addressed by id once deployed (captures pick a link by
      // it), so ids invented here must be saved: start out dirty.
      const changed = report.filledConnectionIds > 0;
      s.savedTopology = changed ? null : t;
      s.dirty = changed;
    }, false, 'loadTopology'),

  newTopology: (name) =>
    set((s) => {
      const t = normalizeTopology(createEmptyTopology(name));
      s.topology = t;
      s.savedTopology = t;
      s.dirty = false;
    }, false, 'newTopology'),

  setTopologyMeta: (meta) =>
    set((s) => {
      if (meta.name !== undefined) s.topology.name = meta.name;
      if (meta.description !== undefined) s.topology.description = meta.description;
      s.dirty = true;
    }, false, 'setTopologyMeta'),

  markClean: () => set({ savedTopology: get().topology, dirty: false }, false, 'markClean'),

  // ── Sites ──
  addSite: (input) => {
    const id = generateId('site');
    set((s) => {
      const position = input.position ?? nextFreePosition(rects(s.topology.sites, NODE_SIZE.site), NODE_SIZE.site);
      s.topology.sites.push({ id, name: input.name, location: input.location ?? '', position, subnets: [], subnetConnections: [] });
      s.dirty = true;
    }, false, 'addSite');
    return id;
  },

  updateSite: (siteId, updates) =>
    set((s) => {
      const site = s.topology.sites.find((x) => x.id === siteId);
      if (!site) return;
      Object.assign(site, updates);
      s.dirty = true;
    }, false, 'updateSite'),

  // ── Subnets ──
  addSubnet: (input) => {
    const site = get().topology.sites.find((x) => x.id === input.siteId);
    if (!site) return null;
    const id = generateId('subnet');
    set((s) => {
      const st = s.topology.sites.find((x) => x.id === input.siteId)!;
      const position = input.position ?? nextFreePosition(rects(st.subnets, NODE_SIZE.subnet), NODE_SIZE.subnet);
      const subnet: Subnet = { id, name: input.name, cidr: input.cidr, containers: [], connections: [], position };
      if (input.autoInfra !== false) {
        const routerIp = getNextAvailableIp(input.cidr, []) ?? '';
        const switchIp = getNextAvailableIp(input.cidr, routerIp ? [routerIp] : []) ?? '';
        const routerId = generateId('node');
        const switchId = generateId('node');
        subnet.gateway = routerIp;
        subnet.containers.push(
          { id: routerId, name: `${input.name} Router`, type: 'router', ip: routerIp, position: { x: 0, y: 0 } },
          { id: switchId, name: `${input.name} Switch`, type: 'switch', ip: switchIp, position: { x: 0, y: NODE_SIZE.device.height + 72 } },
        );
        subnet.connections.push({ id: generateId('c'), from: switchId, to: routerId });
      }
      st.subnets.push(subnet);
      s.dirty = true;
    }, false, 'addSubnet');
    return id;
  },

  updateSubnet: (subnetId, updates) =>
    set((s) => {
      const hit = locate(s.topology as TopologyData, subnetId);
      if (hit?.kind !== 'subnet') return;
      Object.assign(hit.subnet, updates);
      s.dirty = true;
    }, false, 'updateSubnet'),

  // ── Containers ──
  addContainer: (input) => {
    const hit = locate(get().topology, input.subnetId);
    if (hit?.kind !== 'subnet') return null;
    const id = generateId('node');
    set((s) => {
      const h = locate(s.topology as TopologyData, input.subnetId);
      if (h?.kind !== 'subnet') return;
      const { subnet } = h;
      const taken = usedIpsInSubnet(s.topology as TopologyData, subnet.id);
      const ip = input.ip ?? getNextAvailableIp(subnet.cidr, taken) ?? '';
      const name = input.name?.trim() || nextName(subnet.containers.map((c) => c.name), displayNameFor(input.type));
      const position = input.position ?? nextFreePosition(rects(subnet.containers, NODE_SIZE.device), NODE_SIZE.device);
      const container: Container = { id, name, type: input.type, ip, position };
      if (input.image) container.image = input.image;
      if (input.metadata && Object.keys(input.metadata).length) container.metadata = input.metadata;
      if (input.persistencePaths?.length) container.persistencePaths = input.persistencePaths;
      if (input.config && Object.keys(input.config).length) container.config = input.config;
      subnet.containers.push(container);
      if (isRouterType(input.type) && !subnet.gateway) subnet.gateway = ip;
      s.dirty = true;
    }, false, 'addContainer');
    return id;
  },

  updateContainer: (containerId, updates) =>
    set((s) => {
      const hit = locate(s.topology as TopologyData, containerId);
      if (hit?.kind !== 'container') return;
      Object.assign(hit.container, updates);
      // Drop keys explicitly set to undefined so they don't linger as nulls in JSON.
      for (const [k, v] of Object.entries(updates)) if (v === undefined) delete hit.container[k];
      if (hit.subnet.gateway === undefined && isRouterType(hit.container.type)) hit.subnet.gateway = hit.container.ip;
      s.dirty = true;
    }, false, 'updateContainer'),

  // ── Interface legs (multi-homing) ──
  addInterface: (containerId, subnetId) =>
    set((s) => {
      const top = s.topology as TopologyData;
      const c = locate(top, containerId);
      const sub = locate(top, subnetId);
      if (c?.kind !== 'container' || sub?.kind !== 'subnet') return;
      if (!canTakeInterfaceLegs(c.container.type)) return; // a switch would bridge the two subnets
      if (c.subnet.id === subnetId) return; // can't leg into its own home subnet
      const legs = c.container.interfaces ?? [];
      if (legs.some((l) => l.subnetId === subnetId)) return; // already attached
      const ip = getNextAvailableIp(sub.subnet.cidr, usedIpsInSubnet(top, subnetId)) ?? '';
      c.container.interfaces = [...legs, { subnetId, ip }];
      s.dirty = true;
    }, false, 'addInterface'),

  updateInterfaceIp: (containerId, subnetId, ip) =>
    set((s) => {
      const hit = locate(s.topology as TopologyData, containerId);
      if (hit?.kind !== 'container' || !hit.container.interfaces) return;
      const leg = hit.container.interfaces.find((l) => l.subnetId === subnetId);
      if (!leg) return;
      leg.ip = ip;
      s.dirty = true;
    }, false, 'updateInterfaceIp'),

  removeInterface: (containerId, subnetId) =>
    set((s) => {
      const hit = locate(s.topology as TopologyData, containerId);
      if (hit?.kind !== 'container' || !hit.container.interfaces) return;
      hit.container.interfaces = hit.container.interfaces.filter((l) => l.subnetId !== subnetId);
      if (!hit.container.interfaces.length) delete hit.container.interfaces;
      s.dirty = true;
    }, false, 'removeInterface'),

  // ── Connections ──
  addConnection: ({ from, to, label }) => {
    if (from === to) return null;
    const t = get().topology;
    const a = locate(t, from);
    const b = locate(t, to);
    if (!a || !b) return null;
    const id = generateId('c');
    let added = false;
    const conn = (extra: Partial<Connection>): Connection => ({ id, ...extra, ...(label ? { label } : {}) } as Connection);

    set((s) => {
      const top = s.topology as TopologyData;
      const A = locate(top, from)!;
      const B = locate(top, to)!;

      // site ↔ site
      if (A.kind === 'site' && B.kind === 'site') {
        if (hasConnection(top.siteConnections, A.site.id, B.site.id)) return;
        top.siteConnections.push(conn({ from: A.site.id, to: B.site.id, fromContainer: siteRouter(A.site)?.id, toContainer: siteRouter(B.site)?.id }));
        added = true;
      }
      // subnet ↔ subnet
      else if (A.kind === 'subnet' && B.kind === 'subnet') {
        if (A.site.id === B.site.id) {
          if (hasConnection(A.site.subnetConnections, A.subnet.id, B.subnet.id)) return;
          const fc = ensureRouter(top, A.subnet);
          const tc = ensureRouter(top, B.subnet);
          A.site.subnetConnections.push(conn({ from: A.subnet.id, to: B.subnet.id, fromContainer: fc, toContainer: tc }));
        } else {
          if (hasConnection(top.siteConnections, A.site.id, B.site.id)) return;
          const fc = ensureRouter(top, A.subnet);
          const tc = ensureRouter(top, B.subnet);
          top.siteConnections.push(conn({ from: A.site.id, to: B.site.id, fromContainer: fc, toContainer: tc }));
        }
        added = true;
      }
      // container ↔ container
      else if (A.kind === 'container' && B.kind === 'container') {
        if (A.subnet.id === B.subnet.id) {
          if (hasConnection(A.subnet.connections, from, to)) return;
          A.subnet.connections.push(conn({ from, to }));
        } else if (!isRouterType(A.container.type) || !isRouterType(B.container.type)) {
          return; // only routers link across subnets/sites
        } else if (A.site.id === B.site.id) {
          if (hasConnection(A.site.subnetConnections, A.subnet.id, B.subnet.id)) return;
          A.site.subnetConnections.push(conn({ from: A.subnet.id, to: B.subnet.id, fromContainer: from, toContainer: to }));
        } else {
          if (hasConnection(top.siteConnections, A.site.id, B.site.id)) return;
          top.siteConnections.push(conn({ from: A.site.id, to: B.site.id, fromContainer: from, toContainer: to }));
        }
        added = true;
      }
      // subnet ↔ router container (same site)
      else if ((A.kind === 'subnet' && B.kind === 'container') || (A.kind === 'container' && B.kind === 'subnet')) {
        const sub = A.kind === 'subnet' ? A : (B as Extract<typeof B, { kind: 'subnet' }>);
        const con = A.kind === 'container' ? A : (B as Extract<typeof B, { kind: 'container' }>);
        if (sub.site.id !== con.site.id || sub.subnet.id === con.subnet.id) return;
        if (!isRouterType(con.container.type)) return;
        if (hasConnection(sub.site.subnetConnections, sub.subnet.id, con.subnet.id)) return;
        const subRouter = ensureRouter(top, sub.subnet);
        const fromIsSub = A.kind === 'subnet';
        sub.site.subnetConnections.push(
          conn({
            from: fromIsSub ? sub.subnet.id : con.subnet.id,
            to: fromIsSub ? con.subnet.id : sub.subnet.id,
            fromContainer: fromIsSub ? subRouter : con.container.id,
            toContainer: fromIsSub ? con.container.id : subRouter,
          }),
        );
        added = true;
      }
      if (added) s.dirty = true;
    }, false, 'addConnection');
    return added ? id : null;
  },

  updateConnection: (id, updates) =>
    set((s) => {
      const hit = locateConnection(s.topology as TopologyData, id);
      if (!hit) return;
      Object.assign(hit.connection, updates);
      for (const [k, v] of Object.entries(updates)) if (v === undefined) delete hit.connection[k];
      s.dirty = true;
    }, false, 'updateConnection'),

  deleteConnections: (ids) => set((s) => { dropConnections(s.topology as TopologyData, ids); s.dirty = true; }, false, 'deleteConnections'),

  setTrafficFlows: (flows) =>
    set((s) => {
      const t = s.topology as TopologyData;
      t.traffic = { ...(t.traffic ?? {}), flows: JSON.parse(JSON.stringify(flows)) as SavedFlow[] };
      s.dirty = true;
    }, false, 'setTrafficFlows'),

  // ── Scenarios (classroom step-through; part of the saved design, undoable) ──
  addScenario: (name) => {
    const id = generateId('scenario');
    set((s) => {
      const t = s.topology as TopologyData;
      const scenarios = (t.scenarios ??= []);
      scenarios.push({ id, name: name?.trim() || `Scenario ${scenarios.length + 1}`, phases: [] });
      s.dirty = true;
    }, false, 'addScenario');
    return id;
  },

  updateScenario: (scenarioId, updates) =>
    set((s) => {
      const scenario = (s.topology as TopologyData).scenarios?.find((x) => x.id === scenarioId);
      if (!scenario) return;
      Object.assign(scenario, updates);
      s.dirty = true;
    }, false, 'updateScenario'),

  removeScenario: (scenarioId) =>
    set((s) => {
      const t = s.topology as TopologyData;
      if (!t.scenarios) return;
      t.scenarios = t.scenarios.filter((x) => x.id !== scenarioId);
      s.dirty = true;
    }, false, 'removeScenario'),

  addPhase: (scenarioId, name) => {
    const id = generateId('phase');
    let ok = false;
    set((s) => {
      const scenario = (s.topology as TopologyData).scenarios?.find((x) => x.id === scenarioId);
      if (!scenario) return;
      const phases = (scenario.phases ??= []);
      phases.push({ id, name: name?.trim() || `Phase ${phases.length + 1}`, executions: [] });
      ok = true;
      s.dirty = true;
    }, false, 'addPhase');
    return ok ? id : null;
  },

  updatePhase: (phaseId, updates) =>
    set((s) => {
      const phase = findPhase(s.topology as TopologyData, phaseId);
      if (!phase) return;
      Object.assign(phase, updates);
      s.dirty = true;
    }, false, 'updatePhase'),

  removePhase: (phaseId) =>
    set((s) => {
      for (const scenario of (s.topology as TopologyData).scenarios ?? []) {
        const before = scenario.phases?.length ?? 0;
        scenario.phases = (scenario.phases ?? []).filter((p) => p.id !== phaseId);
        if ((scenario.phases.length ?? 0) !== before) { s.dirty = true; return; }
      }
    }, false, 'removePhase'),

  addStep: (phaseId, step) =>
    set((s) => {
      const phase = findPhase(s.topology as TopologyData, phaseId);
      if (!phase) return;
      (phase.executions ??= []).push({
        containerId: step.containerId,
        script: step.script,
        ...(step.args?.length ? { args: [...step.args] } : {}),
      } as ScriptExecution);
      s.dirty = true;
    }, false, 'addStep'),

  updateStep: (phaseId, index, updates) =>
    set((s) => {
      const phase = findPhase(s.topology as TopologyData, phaseId);
      const step = phase?.executions?.[index];
      if (!step) return;
      Object.assign(step, updates);
      if ('args' in updates && !(updates.args?.length)) delete step.args;
      s.dirty = true;
    }, false, 'updateStep'),

  removeStep: (phaseId, index) =>
    set((s) => {
      const phase = findPhase(s.topology as TopologyData, phaseId);
      if (!phase?.executions || index < 0 || index >= phase.executions.length) return;
      phase.executions.splice(index, 1);
      s.dirty = true;
    }, false, 'removeStep'),

  moveStep: (phaseId, from, to) =>
    set((s) => {
      const phase = findPhase(s.topology as TopologyData, phaseId);
      const steps = phase?.executions;
      if (!steps || from < 0 || from >= steps.length || to < 0 || to >= steps.length || from === to) return;
      const [moved] = steps.splice(from, 1);
      steps.splice(to, 0, moved);
      s.dirty = true;
    }, false, 'moveStep'),

  // ── Tutorials (part of the saved design, undoable). Cells on a deleted node
  // are kept, not scrubbed: the panel flags them so their command isn't lost. ──
  addTutorial: (title) => {
    const id = generateId('tutorial');
    set((s) => {
      const t = s.topology as TopologyData;
      const tutorials = (t.tutorials ??= []);
      tutorials.push({ id, title: title?.trim() || `Tutorial ${tutorials.length + 1}`, cells: [] });
      s.dirty = true;
    }, false, 'addTutorial');
    return id;
  },

  updateTutorial: (tutorialId, updates) =>
    set((s) => {
      const tutorial = findTutorial(s.topology as TopologyData, tutorialId);
      if (!tutorial) return;
      Object.assign(tutorial, updates);
      s.dirty = true;
    }, false, 'updateTutorial'),

  removeTutorial: (tutorialId) =>
    set((s) => {
      const t = s.topology as TopologyData;
      if (!t.tutorials?.some((x) => x.id === tutorialId)) return;
      t.tutorials = t.tutorials.filter((x) => x.id !== tutorialId);
      s.dirty = true;
    }, false, 'removeTutorial'),

  duplicateTutorial: (tutorialId) => {
    const source = findTutorial(get().topology as TopologyData, tutorialId);
    if (!source) return null;
    const id = generateId('tutorial');
    const copy = JSON.parse(JSON.stringify(source)) as Tutorial;
    copy.id = id;
    copy.title = `${source.title} (copy)`;
    copy.cells = (copy.cells ?? []).map((c) => ({ ...c, id: generateId('cell') }));
    set((s) => {
      const tutorials = (s.topology as TopologyData).tutorials ?? [];
      const at = tutorials.findIndex((x) => x.id === tutorialId);
      tutorials.splice(at + 1, 0, copy);
      s.dirty = true;
    }, false, 'duplicateTutorial');
    return id;
  },

  addTutorialCell: (tutorialId, kind, index, init) => {
    const cell = makeCell(kind, init);
    let ok = false;
    set((s) => {
      const tutorial = findTutorial(s.topology as TopologyData, tutorialId);
      if (!tutorial) return;
      const cells = (tutorial.cells ??= []);
      const at = index === undefined ? cells.length : Math.max(0, Math.min(index, cells.length));
      cells.splice(at, 0, cell);
      ok = true;
      s.dirty = true;
    }, false, 'addTutorialCell');
    return ok ? cell.id : null;
  },

  updateTutorialCell: (tutorialId, cellId, updates) =>
    set((s) => {
      const cell = findTutorial(s.topology as TopologyData, tutorialId)?.cells?.find((c) => c.id === cellId);
      if (!cell) return;
      if (cell.kind === 'markdown') {
        if (updates.source !== undefined) cell.source = updates.source;
      } else {
        if (updates.containerId !== undefined) cell.containerId = updates.containerId;
        if (updates.command !== undefined) cell.command = updates.command;
      }
      s.dirty = true;
    }, false, 'updateTutorialCell'),

  removeTutorialCell: (tutorialId, cellId) =>
    set((s) => {
      const tutorial = findTutorial(s.topology as TopologyData, tutorialId);
      const at = tutorial?.cells?.findIndex((c) => c.id === cellId) ?? -1;
      if (!tutorial || at < 0) return;
      tutorial.cells.splice(at, 1);
      s.dirty = true;
    }, false, 'removeTutorialCell'),

  moveTutorialCell: (tutorialId, from, to) =>
    set((s) => {
      const cells = findTutorial(s.topology as TopologyData, tutorialId)?.cells;
      if (!cells || from < 0 || from >= cells.length || to < 0 || to >= cells.length || from === to) return;
      const [moved] = cells.splice(from, 1);
      cells.splice(to, 0, moved);
      s.dirty = true;
    }, false, 'moveTutorialCell'),

  deleteNodes: (ids) => set((s) => { dropNodes(s.topology as TopologyData, ids); s.dirty = true; }, false, 'deleteNodes'),

  deleteItems: (nodeIds, edgeIds) =>
    set((s) => {
      const top = s.topology as TopologyData;
      if (edgeIds.length) dropConnections(top, edgeIds);
      if (nodeIds.length) dropNodes(top, nodeIds);
      s.dirty = true;
    }, false, 'deleteItems'),

  duplicateNodes: (ids) => {
    const created: string[] = [];
    set((s) => {
      const top = s.topology as TopologyData;
      for (const id of ids) {
        const hit = locate(top, id);
        if (!hit) continue;
        if (hit.kind === 'container') {
          const { subnet, container } = hit;
          const taken = usedIpsInSubnet(top, subnet.id);
          const copy: Container = {
            ...JSON.parse(JSON.stringify(container)),
            id: generateId('node'),
            name: nextName(subnet.containers.map((c) => c.name), container.name.replace(/\s+\d+$/, '')),
            ip: getNextAvailableIp(subnet.cidr, taken) ?? '',
            position: { x: (container.position?.x ?? 0) + OFFSET, y: (container.position?.y ?? 0) + OFFSET },
          };
          rehomeCopy(top, copy);
          subnet.containers.push(copy);
          created.push(copy.id);
        } else if (hit.kind === 'subnet') {
          const { site, subnet } = hit;
          const map = new Map<string, string>();
          const containers = subnet.containers.map((c) => {
            const nid = generateId('node');
            map.set(c.id, nid);
            return { ...JSON.parse(JSON.stringify(c)), id: nid } as Container;
          });
          containers.forEach((c) => rehomeCopy(top, c, map));
          const copy: Subnet = {
            ...JSON.parse(JSON.stringify(subnet)),
            id: generateId('subnet'),
            name: nextName(site.subnets.map((x) => x.name), subnet.name.replace(/\s+\d+$/, '')),
            containers,
            connections: remapIds(subnet.connections, map),
            position: { x: (subnet.position?.x ?? 0) + OFFSET, y: (subnet.position?.y ?? 0) + OFFSET },
          };
          site.subnets.push(copy);
          created.push(copy.id);
        } else {
          const { site } = hit;
          const map = new Map<string, string>();
          const subnets = site.subnets.map((sn) => {
            const nsid = generateId('subnet');
            map.set(sn.id, nsid);
            const containers = sn.containers.map((c) => {
              const nid = generateId('node');
              map.set(c.id, nid);
              return { ...JSON.parse(JSON.stringify(c)), id: nid } as Container;
            });
            return { ...JSON.parse(JSON.stringify(sn)), id: nsid, containers, connections: remapIds(sn.connections, map) } as Subnet;
          });
          // Legs/mirrors are remapped once every subnet and device of the copy has its new id.
          subnets.forEach((sn) => sn.containers.forEach((c) => rehomeCopy(top, c, map)));
          const copy: Site = {
            ...JSON.parse(JSON.stringify(site)),
            id: generateId('site'),
            name: nextName(top.sites.map((x) => x.name), site.name.replace(/\s+\d+$/, '')),
            subnets,
            subnetConnections: remapIds(site.subnetConnections, map),
            position: { x: site.position.x + OFFSET, y: site.position.y + OFFSET },
          };
          top.sites.push(copy);
          created.push(copy.id);
        }
      }
      if (created.length) s.dirty = true;
    }, false, 'duplicateNodes');
    return created;
  },

  moveNodes: (moves) =>
    set((s) => {
      const top = s.topology as TopologyData;
      let changed = false;
      for (const { id, position } of moves) {
        const hit = locate(top, id);
        if (!hit) continue;
        const target = hit.kind === 'site' ? hit.site : hit.kind === 'subnet' ? hit.subnet : hit.container;
        if (target.position?.x === position.x && target.position?.y === position.y) continue;
        target.position = { x: Math.round(position.x), y: Math.round(position.y) };
        changed = true;
      }
      if (changed) s.dirty = true;
    }, false, 'moveNodes'),

  applyLayout: (scope, mode, sizes) => {
    const positions = layoutScope(get().topology, scope, mode, { sizes });
    get().moveNodes([...positions.entries()].map(([id, position]) => ({ id, position })));
  },
});
