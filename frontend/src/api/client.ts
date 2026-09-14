import type { TopologyData } from '../types/topology';
import type { Catalog } from '../catalog/catalog';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** Extract a readable message from a FastAPI error body or a thrown error. */
export function errorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (err instanceof ApiError) {
    try {
      const parsed = JSON.parse(err.message) as { detail?: unknown };
      if (typeof parsed.detail === 'string') return parsed.detail;
      if (Array.isArray(parsed.detail)) return parsed.detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ');
    } catch { /* not JSON */ }
    return err.message || fallback;
  }
  if (err instanceof Error) return err.message || fallback;
  return fallback;
}

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
// There is no sign-in screen: the backend leaves its API open unless
// AE3GIS_INSTRUCTOR_TOKEN is set. When it is, build/run the frontend with a
// matching VITE_INSTRUCTOR_TOKEN and every request carries it automatically.
const AUTH_TOKEN: string | null = import.meta.env.VITE_INSTRUCTOR_TOKEN?.trim() || null;

export function getAuthToken(): string | null { return AUTH_TOKEN; }

/** WebSocket URL with the auth token as a query param (browsers can't set
 *  headers on WS upgrades). */
export function wsUrl(path: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const base = `${protocol}//${window.location.host}${path}`;
  return AUTH_TOKEN ? `${base}?token=${encodeURIComponent(AUTH_TOKEN)}` : base;
}

// ── Helpers ────────────────────────────────────────────────────────
const BASE = '/api/topologies';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (AUTH_TOKEN) headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
  const initHeaders = init?.headers;
  if (initHeaders) {
    if (initHeaders instanceof Headers) initHeaders.forEach((v, k) => { headers[k] = v; });
    else if (Array.isArray(initHeaders)) for (const [k, v] of initHeaders) headers[k] = v;
    else Object.assign(headers, initHeaders);
  }
  const res = await fetch(url, { ...init, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, text || res.statusText);
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
  if (AUTH_TOKEN) headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
  const res = await fetch(`${BASE}/import-json`, { method: 'POST', headers, body: form });
  if (!res.ok) throw new ApiError(res.status, await res.text().catch(() => res.statusText));
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
