// ── Types ──────────────────────────────────────────────────────────

export type ContainerType =
  | 'web-server'
  | 'file-server'
  | 'plc'
  | 'firewall'
  | 'switch'
  | 'router'
  | 'workstation';

export interface Container {
  id: string;
  name: string;
  type: ContainerType;
  ip: string;
  kind?: string;
  image?: string;
  status?: 'running' | 'stopped' | 'paused';
  metadata?: Record<string, string>;
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

export interface TopologyData {
  name?: string;
  sites: Site[];
  siteConnections: Connection[];
}

// ── Data (loaded from JSON) ───────────────────────────────────────

import topologyJson from './topology.json';

export const sampleTopology: TopologyData = topologyJson as TopologyData;
