// Shared domain types — the single source of truth for topology shape.
// (Moved out of the old types/topology.ts.) ContainerType is a plain
// string: the set of valid types is data, served by the backend catalog.

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
