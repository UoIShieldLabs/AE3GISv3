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
// container `id`, container `name`/`type`/`ip`/`image`, subnet `cidr`/`gateway`,
// connection `from`/`to`/`fromContainer`/`toContainer`/`fromInterface`/
// `toInterface`, and topology `name`. Everything else is editor-only.

export type ContainerType = string;

export interface Position {
  x: number;
  y: number;
}

export interface Container {
  id: string;
  name: string;
  type: ContainerType;
  ip: string;
  kind?: string;
  image?: string;
  /** Legacy desired-state field; the engine ignores it and the editor no longer writes it. */
  status?: 'running' | 'stopped' | 'paused';
  config?: Record<string, unknown>;
  metadata?: Record<string, string>;
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
}

export interface AttackPhase {
  id: string;
  name: string;
  description?: string;
  executions: ScriptExecution[];
}

export interface Scenario {
  id: string;
  name: string;
  description?: string;
  phases: AttackPhase[];
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
