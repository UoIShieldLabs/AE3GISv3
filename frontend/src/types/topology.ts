// Frontend-owned topology types.
//
// These are the FRONTEND's own view of topology data and are deliberately NOT
// synced with the backend. The backend persists and serves topology `data` as
// opaque JSON (it does not model these fields), so this file can add, rename,
// or drop fields with no backend change. Container carries an index signature
// so unknown fields coming from the backend round-trip through the editor
// untouched. The set of valid container types is data, served by the backend
// catalog (GET /api/catalog).

export type ContainerType = string;

export interface Container {
  id: string;
  name: string;
  type: ContainerType;
  ip: string;
  kind?: string;
  image?: string;
  status?: 'running' | 'stopped' | 'paused';
  config?: Record<string, unknown>;
  metadata?: Record<string, string>;
  persistencePaths?: string[];
  // Unknown fields from the backend pass through untouched (see header).
  [key: string]: unknown;
}

export interface Connection {
  from: string;
  to: string;
  label?: string;
  fromInterface?: string;
  toInterface?: string;
  fromContainer?: string;
  toContainer?: string;
}

export interface Subnet {
  id: string;
  name: string;
  cidr: string;
  gateway?: string;
  containers: Container[];
  connections: Connection[];
}

export interface Site {
  id: string;
  name: string;
  location: string;
  position: { x: number; y: number };
  subnets: Subnet[];
  subnetConnections: Connection[];
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

export interface TopologyData {
  name?: string;
  sites: Site[];
  siteConnections: Connection[];
  scenarios?: Scenario[];
}

// An empty topology — the default app state (no bundled demo network).
export const emptyTopology: TopologyData = { sites: [], siteConnections: [] };
