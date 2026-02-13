import type { TopologyData } from '../data/sampleTopology';

// ── Types ──────────────────────────────────────────────────────────

export interface TopologySummary {
  id: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TopologyRecord extends TopologySummary {
  data: TopologyData;
  clab_yaml: string | null;
}

export interface ClabContainer {
  name: string;
  state: string;
  'ipv4-address'?: string;
  'ipv6-address'?: string;
  image?: string;
  kind?: string;
  'container-id'?: string;
  'short-id'?: string;
  group?: string;
  labels?: Record<string, string>;
  'network-namespace'?: string;
}

// ── Helpers ────────────────────────────────────────────────────────

const BASE = '/api/topologies';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function json(body: unknown): RequestInit {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

// ── CRUD ───────────────────────────────────────────────────────────

export function listTopologies(): Promise<TopologySummary[]> {
  return request<TopologySummary[]>(BASE);
}

export function createTopology(name: string, data: TopologyData): Promise<TopologyRecord> {
  return request<TopologyRecord>(BASE, { method: 'POST', ...json({ name, data }) });
}

export function getTopology(id: string): Promise<TopologyRecord> {
  return request<TopologyRecord>(`${BASE}/${id}`);
}

export function updateTopology(
  id: string,
  name?: string,
  data?: TopologyData,
): Promise<TopologyRecord> {
  const body: Record<string, unknown> = {};
  if (name !== undefined) body.name = name;
  if (data !== undefined) body.data = data;
  return request<TopologyRecord>(`${BASE}/${id}`, { method: 'PUT', ...json(body) });
}

export function deleteTopology(id: string): Promise<void> {
  return request<void>(`${BASE}/${id}`, { method: 'DELETE' });
}

// ── ContainerLab ───────────────────────────────────────────────────

export function deployTopology(id: string): Promise<{ status: string; output: string }> {
  return request(`${BASE}/${id}/deploy`, { method: 'POST' });
}

export function destroyTopology(id: string): Promise<{ status: string; output: string }> {
  return request(`${BASE}/${id}/destroy`, { method: 'POST' });
}

export function getTopologyStatus(
  id: string,
): Promise<{ status: string; containers: ClabContainer[] }> {
  return request(`${BASE}/${id}/status`);
}
