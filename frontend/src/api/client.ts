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

export interface FirewallRuleRecord {
  source: string;
  destination: string;
  protocol: 'any' | 'tcp' | 'udp' | 'icmp';
  port: string;
  action: 'accept' | 'drop';
}

// ── Auth token ────────────────────────────────────────────────────

let _authToken: string | null = null;

export function setAuthToken(token: string | null) {
  _authToken = token;
}

export function getAuthToken(): string | null {
  return _authToken;
}

/**
 * Build a WebSocket URL with the auth token appended as a query parameter.
 * Browsers cannot set custom headers on WebSocket connections.
 */
export function wsUrl(path: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const base = `${protocol}//${window.location.host}${path}`;
  return _authToken ? `${base}?token=${encodeURIComponent(_authToken)}` : base;
}

// ── Helpers ────────────────────────────────────────────────────────

const BASE = '/api/topologies';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (_authToken) {
    headers['Authorization'] = `Bearer ${_authToken}`;
  }

  // Merge caller-provided headers (e.g. Content-Type from json())
  const initHeaders = init?.headers;
  if (initHeaders) {
    if (initHeaders instanceof Headers) {
      initHeaders.forEach((v, k) => { headers[k] = v; });
    } else if (Array.isArray(initHeaders)) {
      for (const [k, v] of initHeaders) headers[k] = v;
    } else {
      Object.assign(headers, initHeaders);
    }
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

export async function importTopology(name: string, file: File): Promise<TopologySummary> {
  const form = new FormData();
  form.append('name', name);
  form.append('file', file);
  const headers: Record<string, string> = {};
  if (_authToken) headers['Authorization'] = `Bearer ${_authToken}`;
  const res = await fetch(`${BASE}/import`, { method: 'POST', headers, body: form });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

// ── ContainerLab ───────────────────────────────────────────────────

export function deployTopology(id: string): Promise<{ status: string; output: string }> {
  return request(`${BASE}/${id}/deploy`, { method: 'POST' });
}

export function generateTopology(id: string): Promise<{ yaml: string }> {
  return request(`${BASE}/${id}/generate`, { method: 'POST' });
}

export function destroyTopology(id: string): Promise<{ status: string; output: string }> {
  return request(`${BASE}/${id}/destroy`, { method: 'POST' });
}

export function getTopologyStatus(
  id: string,
): Promise<{ status: string; containers: ClabContainer[] }> {
  return request(`${BASE}/${id}/status`);
}

export function getFirewallRules(
  topologyId: string,
  containerId: string,
): Promise<{ rules: FirewallRuleRecord[] }> {
  return request(`${BASE}/${topologyId}/firewall/${containerId}`);
}

export function putFirewallRules(
  topologyId: string,
  containerId: string,
  rules: FirewallRuleRecord[],
): Promise<{ rules: FirewallRuleRecord[] }> {
  return request(`${BASE}/${topologyId}/firewall/${containerId}`, {
    method: 'PUT',
    ...json({ rules }),
  });
}

// ── Classroom ─────────────────────────────────────────────────────

export interface ClassSessionRecord {
  id: string;
  name: string;
  template_id: string;
  created_at: string;
  updated_at: string;
}

export interface StudentSlotRecord {
  id: string;
  session_id: string;
  topology_id: string;
  join_code: string;
  label: string | null;
  created_at: string;
}

const CLASSROOM = '/api/classroom';

export function studentLogin(
  joinCode: string,
): Promise<{ role: string; token: string; topology_id: string | null }> {
  return request(`${CLASSROOM}/login`, {
    method: 'POST',
    ...json({ join_code: joinCode }),
  });
}

export function listSessions(): Promise<ClassSessionRecord[]> {
  return request<ClassSessionRecord[]>(`${CLASSROOM}/sessions`);
}

export function createSession(
  name: string,
  templateId: string,
): Promise<ClassSessionRecord> {
  return request<ClassSessionRecord>(`${CLASSROOM}/sessions`, {
    method: 'POST',
    ...json({ name, template_id: templateId }),
  });
}

export function deleteSession(id: string): Promise<void> {
  return request<void>(`${CLASSROOM}/sessions/${id}`, { method: 'DELETE' });
}

export function instantiateSession(
  sessionId: string,
  count: number,
  labelPrefix: string = 'Student',
): Promise<StudentSlotRecord[]> {
  return request<StudentSlotRecord[]>(
    `${CLASSROOM}/sessions/${sessionId}/instantiate`,
    { method: 'POST', ...json({ count, label_prefix: labelPrefix }) },
  );
}

export function listSlots(sessionId: string): Promise<StudentSlotRecord[]> {
  return request<StudentSlotRecord[]>(`${CLASSROOM}/sessions/${sessionId}/slots`);
}

export function deleteSlot(sessionId: string, slotId: string): Promise<void> {
  return request<void>(
    `${CLASSROOM}/sessions/${sessionId}/slots/${slotId}`,
    { method: 'DELETE' },
  );
}
