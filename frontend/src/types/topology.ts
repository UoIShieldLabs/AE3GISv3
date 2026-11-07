// Frontend-owned topology types.
//
// These are the FRONTEND's own view of topology data and are deliberately NOT
// synced with the backend. The backend persists and serves topology `data` as
// opaque JSON (it does not model these fields), so this file can add, rename,
// or drop fields with no backend change. Entities carry an index signature so
// unknown fields coming from the backend round-trip through the editor
// untouched. The set of valid container types is data, served by the backend
// catalog (GET /api/catalog).
//
// Fields the deployment engine reads (backend/domain/plan.py): site/subnet/
// container `id`, container `name`/`type`/`ip`/`image`/`interfaces`/`mirrorTo`,
// subnet `cidr`/`gateway`, connection `from`/`to`/`fromContainer`/`toContainer`/
// `fromInterface`/`toInterface`, and topology `name`. Everything else is editor-only.

export type ContainerType = string;

export interface Position {
  x: number;
  y: number;
}

/** An extra network interface leg on a container (multi-homing): the node
 *  attaches to another subnet beyond its home, with its own IP there. */
export interface NetworkInterface {
  /** Id of the subnet this leg attaches to (a different subnet in the topology). */
  subnetId: string;
  /** This node's IP on that subnet (must be inside the subnet's CIDR). */
  ip: string;
  [key: string]: unknown;
}

export interface Container {
  id: string;
  name: string;
  type: ContainerType;
  ip: string;
  /** Extra interface legs beyond the home subnet. The home-subnet IP stays in
   *  `ip` (eth0); each leg becomes another addressed interface at deploy time. */
  interfaces?: NetworkInterface[];
  /** HTTP port this node serves a web UI on (process-sim, an HMI console).
   *  Relayed to the browser via GET /topologies/{id}/webui/{node}/. Falls back
   *  to the catalog type's webUiPort when unset. */
  webUiPort?: number;
  /** Open vSwitch switches only: mirror all bridge traffic to this node's port
   *  (SPAN), so a passive IDS on that link sees unicast it would otherwise miss. */
  mirrorTo?: string;
  kind?: string;
  image?: string;
  /** Legacy desired-state field; the engine ignores it and the editor no longer writes it. */
  status?: 'running' | 'stopped' | 'paused';
  config?: Record<string, unknown>;
  metadata?: Record<string, string>;
  /** Environment variables set on this node at deploy time, applied on top of
   *  the image's catalog env (the node's values win). e.g. point a client at a
   *  peer's IP where the lab has no cross-node name resolution. */
  env?: Record<string, string>;
  persistencePaths?: string[];
  /** Canvas position, relative to the enclosing subnet. Filled by normalizeTopology. */
  position?: Position;
  // Unknown fields from the backend pass through untouched (see header).
  [key: string]: unknown;
}

export interface Connection {
  /** Stable editor id. Always present after normalizeTopology(); optional in
   *  the type only so hand-written/imported JSON without ids still loads. */
  id?: string;
  from: string;
  to: string;
  label?: string;
  fromInterface?: string;
  toInterface?: string;
  fromContainer?: string;
  toContainer?: string;
  [key: string]: unknown;
}

export interface Subnet {
  id: string;
  name: string;
  cidr: string;
  gateway?: string;
  containers: Container[];
  connections: Connection[];
  /** Canvas position, relative to the enclosing site. */
  position?: Position;
  [key: string]: unknown;
}

export interface Site {
  id: string;
  name: string;
  location: string;
  position: Position;
  subnets: Subnet[];
  subnetConnections: Connection[];
  [key: string]: unknown;
}

export interface ScriptExecution {
  containerId: string;
  script: string;
  args?: string[];
  // Unknown fields from the backend/old data pass through untouched.
  [key: string]: unknown;
}

export interface AttackPhase {
  id: string;
  name: string;
  description?: string;
  executions: ScriptExecution[];
  [key: string]: unknown;
}

export interface Scenario {
  id: string;
  name: string;
  description?: string;
  phases: AttackPhase[];
  [key: string]: unknown;
}

/** A note in a tutorial, written in Markdown. */
export interface TutorialMarkdownCell {
  id: string;
  kind: 'markdown';
  source: string;
  [key: string]: unknown;
}

/** A command a tutorial types into a node's terminal (its normal dock tab). */
export interface TutorialCommandCell {
  id: string;
  kind: 'command';
  containerId: string;
  command: string;
  [key: string]: unknown;
}

export type TutorialCell = TutorialMarkdownCell | TutorialCommandCell;

/** A notebook of notes and commands, stepped through on the deployed lab.
 *  Editor-only: the backend never reads it; commands run in the browser's terminals. */
export interface Tutorial {
  id: string;
  title: string;
  cells: TutorialCell[];
  [key: string]: unknown;
}

/** Editor view preferences stored with the topology. */
export interface TopologyView {
  /** Position-format version; bumped when the coordinate model changes. */
  version?: number;
}

/** A traffic flow saved with the design (editor-only: the backend's run API
 *  takes flows inline). */
export interface SavedFlow {
  id: string;
  client: string; // node id
  server: string; // node id
  protocol: 'tcp' | 'udp';
  direction: 'forward' | 'reverse' | 'bidir';
  bitrate?: string | null;
  parallel?: number;
  length?: number | null;
  [key: string]: unknown;
}

export interface TopologyData {
  name?: string;
  description?: string;
  sites: Site[];
  siteConnections: Connection[];
  scenarios?: Scenario[];
  tutorials?: Tutorial[];
  view?: TopologyView;
  /** Traffic flows kept with the design (run from the Traffic panel). */
  traffic?: { flows?: SavedFlow[]; [key: string]: unknown };
  [key: string]: unknown;
}

// An empty topology — the default app state (no bundled demo network).
export const emptyTopology: TopologyData = { sites: [], siteConnections: [] };

export function createEmptyTopology(name?: string): TopologyData {
  return { name, sites: [], siteConnections: [], view: { version: 2 } };
}
