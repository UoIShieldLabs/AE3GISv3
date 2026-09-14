// All REST/WebSocket calls to the backend. Types come from the backend's
// OpenAPI document (npm run api:types -> ./schema.d.ts), so the backend is the
// typed source of truth for the API; only `TopologyData` is frontend-owned.
import type { components } from './schema';
import type { TopologyData } from '../types/topology';

type S = components['schemas'];

export type Diagnostic = S['Diagnostic'];
export type DiagnosticsSummary = S['DiagnosticsSummary'];
export type ValidationResult = S['ValidationResult'];
export type TopologySummary = S['TopologySummary'];
export type TopologyRecord = Omit<S['TopologyRecord'], 'data'> & { data: TopologyData };
export type JobStep = S['JobStep'];
export type Job = S['JobOut'];
export type NodeState = S['NodeState'];
export type Runtime = S['RuntimeOut'];
export type TopologyEvent = S['EventOut'];
export type PlanOut = S['PlanOut'];
export type LabsReport = S['LabsReport'];
export type Lab = S['LabOut'];
export type Health = S['HealthOut'];
export type PresetSummary = S['PresetSummary'];
export type ContextOut = S['ContextOut'];
export type Catalog = import('../catalog/catalog').Catalog;

export type ExportFormat = 'labspec' | 'kathara' | 'containerlab';

export class ApiError extends Error {
  status: number;
  code: string;
  /** Extra fields from the error envelope (e.g. `diagnostics`, `current_version`). */
  data: Record<string, unknown>;
  constructor(status: number, message: string, code = 'error', data: Record<string, unknown> = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

/** Readable message for any thrown error. */
export function errorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (err instanceof ApiError) return err.message || fallback;
  if (err instanceof Error) return err.message || fallback;
  return fallback;
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

// ── Transport ──────────────────────────────────────────────────────
const V1 = '/api/v1';

function authHeaders(): Record<string, string> {
  return AUTH_TOKEN ? { Authorization: `Bearer ${AUTH_TOKEN}` } : {};
}

async function toApiError(res: Response): Promise<ApiError> {
  const text = await res.text().catch(() => '');
  try {
    const body = JSON.parse(text) as { detail?: unknown; code?: string } & Record<string, unknown>;
    const { detail, code, ...rest } = body;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => (d as { msg?: string }).msg ?? String(d)).join('; ')
          : res.statusText;
    return new ApiError(res.status, message, code ?? 'error', rest);
  } catch {
    return new ApiError(res.status, text || res.statusText);
  }
}

async function request<T>(url: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(url, { ...init, headers: { ...authHeaders(), ...(init.headers as Record<string, string> | undefined) } });
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function json(body: unknown, method = 'POST'): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

// ── Catalog ────────────────────────────────────────────────────────
export function fetchCatalog(): Promise<Catalog> {
  return request(`${V1}/catalog`);
}

// ── Topologies ─────────────────────────────────────────────────────
export function listTopologies(): Promise<TopologySummary[]> {
  return request(`${V1}/topologies`);
}
export function createTopology(name: string, data: TopologyData): Promise<TopologyRecord> {
  return request(`${V1}/topologies`, json({ name, data }));
}
export function getTopology(id: string): Promise<TopologyRecord> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}`);
}
export function updateTopology(id: string, patch: { name?: string; data?: TopologyData; version?: number | null }): Promise<TopologyRecord> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}`, json(patch, 'PUT'));
}
export function deleteTopology(id: string): Promise<void> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
export async function importJsonTopology(file: File): Promise<TopologyRecord> {
  const form = new FormData();
  form.append('file', file);
  return request(`${V1}/topologies/import-json`, { method: 'POST', body: form });
}
export function validateTopology(data: TopologyData): Promise<ValidationResult> {
  return request(`${V1}/topologies/validate`, json({ data }));
}
export function getPlan(id: string): Promise<PlanOut> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/plan`);
}
export function getContext(id: string): Promise<ContextOut> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/context`);
}
export function listEvents(id: string, after = 0, limit = 200): Promise<TopologyEvent[]> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/events?after=${after}&limit=${limit}`);
}

/** Fetch an export and hand it to the browser as a download. */
export async function downloadExport(id: string, format: ExportFormat): Promise<void> {
  const res = await fetch(`${V1}/topologies/${encodeURIComponent(id)}/export?format=${format}`, { headers: authHeaders() });
  if (!res.ok) throw await toApiError(res);
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition') ?? '';
  const match = /filename="?([^";]+)"?/.exec(disposition);
  const a = document.createElement('a');
  const url = URL.createObjectURL(blob);
  a.href = url;
  a.download = match?.[1] ?? `topology.${format === 'labspec' ? 'json' : 'zip'}`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Deployment (jobs) ──────────────────────────────────────────────
export function deployTopology(id: string): Promise<Job> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/deploy`, { method: 'POST' });
}
export function destroyTopology(id: string): Promise<Job> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/destroy`, { method: 'POST' });
}
export function getRuntime(id: string): Promise<Runtime> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/runtime`);
}
export function getJob(jobId: string): Promise<Job> {
  return request(`${V1}/jobs/${encodeURIComponent(jobId)}`);
}
export function execWsPath(id: string, containerId: string): string {
  return `${V1}/topologies/ws/${encodeURIComponent(id)}/exec/${encodeURIComponent(containerId)}`;
}

// ── Presets ────────────────────────────────────────────────────────
export function listPresets(): Promise<{ presets: PresetSummary[] }> {
  return request(`${V1}/presets`);
}
export function loadPreset(presetId: string): Promise<TopologyRecord> {
  return request(`${V1}/presets/${encodeURIComponent(presetId)}/load`, { method: 'POST' });
}

// ── System ─────────────────────────────────────────────────────────
export function getHealth(): Promise<Health> {
  return request(`${V1}/system/health`);
}
export function listLabs(): Promise<LabsReport> {
  return request(`${V1}/system/labs`);
}
export function reconcileLabs(): Promise<{ reset: number; orphans: number }> {
  return request(`${V1}/system/reconcile`, { method: 'POST' });
}
export function purgeLab(labHash: string): Promise<{ lab_hash: string; topology_id: string | null }> {
  return request(`${V1}/system/labs/${encodeURIComponent(labHash)}/purge`, { method: 'POST' });
}
