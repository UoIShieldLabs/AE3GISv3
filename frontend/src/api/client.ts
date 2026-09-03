import type { TopologyData } from '../types/topology';
import type { Catalog } from '../catalog/catalog';

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
  engine_state: Record<string, unknown> | null;
}

export interface StatusContainer {
  id: string;
  name: string;
  state: string;
}

// ── Auth token ─────────────────────────────────────────────────────
let _authToken: string | null = null;

export function setAuthToken(token: string | null) { _authToken = token; }
export function getAuthToken(): string | null { return _authToken; }

/** WebSocket URL with the auth token as a query param (browsers can't set
 *  headers on WS upgrades). */
export function wsUrl(path: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const base = `${protocol}//${window.location.host}${path}`;
  return _authToken ? `${base}?token=${encodeURIComponent(_authToken)}` : base;
}

// ── Helpers ────────────────────────────────────────────────────────
const BASE = '/api/topologies';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (_authToken) headers['Authorization'] = `Bearer ${_authToken}`;
  const initHeaders = init?.headers;
  if (initHeaders) {
    if (initHeaders instanceof Headers) initHeaders.forEach((v, k) => { headers[k] = v; });
    else if (Array.isArray(initHeaders)) for (const [k, v] of initHeaders) headers[k] = v;
    else Object.assign(headers, initHeaders);
  }
  const res = await fetch(url, { ...init, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function json(body: unknown): RequestInit {
  return { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

// ── Catalog ────────────────────────────────────────────────────────
export function fetchCatalog(): Promise<Catalog> {
  return request<Catalog>('/api/catalog');
}

// ── Topology CRUD ──────────────────────────────────────────────────
export function listTopologies(): Promise<TopologySummary[]> {
  return request<TopologySummary[]>(BASE);
}
export function createTopology(name: string, data: TopologyData): Promise<TopologyRecord> {
  return request<TopologyRecord>(BASE, { method: 'POST', ...json({ name, data }) });
}
export function getTopology(id: string): Promise<TopologyRecord> {
  return request<TopologyRecord>(`${BASE}/${id}`);
}
export function updateTopology(id: string, name?: string, data?: TopologyData): Promise<TopologyRecord> {
  const body: Record<string, unknown> = {};
  if (name !== undefined) body.name = name;
  if (data !== undefined) body.data = data;
  return request<TopologyRecord>(`${BASE}/${id}`, { method: 'PUT', ...json(body) });
}
export function deleteTopology(id: string): Promise<void> {
  return request<void>(`${BASE}/${id}`, { method: 'DELETE' });
}
export async function importJsonTopology(file: File): Promise<TopologySummary> {
  const form = new FormData();
  form.append('file', file);
  const headers: Record<string, string> = {};
  if (_authToken) headers['Authorization'] = `Bearer ${_authToken}`;
  const res = await fetch(`${BASE}/import-json`, { method: 'POST', headers, body: form });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => res.statusText)}`);
  return res.json();
}

// ── Deployment ─────────────────────────────────────────────────────
export function deployTopology(id: string): Promise<{ status: string; engine_state: unknown }> {
  return request(`${BASE}/${id}/deploy`, { method: 'POST' });
}
export function destroyTopology(id: string): Promise<{ status: string }> {
  return request(`${BASE}/${id}/destroy`, { method: 'POST' });
}
export function getTopologyStatus(id: string): Promise<{ status: string; containers: StatusContainer[] }> {
  return request(`${BASE}/${id}/status`);
}
export function execWsPath(id: string, containerId: string): string {
  return `${BASE}/ws/${id}/exec/${containerId}`;
}

// ── Presets ────────────────────────────────────────────────────────
export interface PresetSummary {
  id: string;
  name: string;
  description: string;
  scenario_count: number;
  site_count: number;
}
const PRESETS = '/api/presets';
export function listPresets(): Promise<{ presets: PresetSummary[] }> {
  return request(`${PRESETS}`);
}
export function loadPreset(presetId: string): Promise<{ id: string; name: string; status: string; created_at: string }> {
  return request(`${PRESETS}/${presetId}/load`, { method: 'POST' });
}
