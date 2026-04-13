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

export async function importJsonTopology(file: File): Promise<TopologySummary> {
  const form = new FormData();
  form.append('file', file);
  const headers: Record<string, string> = {};
  if (_authToken) headers['Authorization'] = `Bearer ${_authToken}`;
  const res = await fetch(`${BASE}/import-json`, { method: 'POST', headers, body: form });
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

// ── Scripts ───────────────────────────────────────────────────────

export interface AvailableScript {
  path: string;
  scriptDir: string;
  containerTypes: string[];
  filename: string;
}

export function listAvailableScripts(): Promise<{ scripts: AvailableScript[] }> {
  return request(`${BASE}/scripts/available`);
}

// ── Scenarios ─────────────────────────────────────────────────────

export interface PhaseExecutionResult {
  containerId: string;
  script: string;
  returncode: number;
  stdout: string;
  stderr: string;
}

export function executePhase(
  topologyId: string,
  scenarioId: string,
  phaseId: string,
): Promise<{ phase_id: string; results: PhaseExecutionResult[] }> {
  return request(
    `${BASE}/${topologyId}/scenarios/${scenarioId}/phases/${phaseId}/execute`,
    { method: 'POST' },
  );
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

// ── Batch Phase Execution ────────────────────────────────────────

export interface PushedExecSession {
  session_id: string;
  container_id: string;
  container_name: string;
  script: string;
  phase_name: string;
}

export interface BatchTopologyResult {
  topology_id: string;
  label: string | null;
  skipped: boolean;
  reason?: string;
  /** Live interactive PTY sessions created for each execution (new style). */
  exec_sessions?: PushedExecSession[];
  skipped_executions?: { containerId: string; script: string; reason: string }[];
  /** Legacy one-shot results — only present for non-batch single-topology execute. */
  results?: PhaseExecutionResult[];
}

export function executePhaseBatch(
  sessionId: string,
  scenarioId: string,
  phaseId: string,
): Promise<{ session_id: string; topology_results: BatchTopologyResult[] }> {
  return request(
    `${CLASSROOM}/sessions/${sessionId}/execute-phase`,
    { method: 'POST', ...json({ scenario_id: scenarioId, phase_id: phaseId }) },
  );
}

// ── AI Chat ─────────────────────────────────────────────────────

export interface AiChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AiToolResult {
  tool: string;
  args: Record<string, unknown>;
  result: string;
}

export interface AiTopologyAction {
  action: 'created' | 'modified';
  topology_id: string;
  name: string;
}

export interface AiScenarioAction {
  scenario_id: string;
  name: string;
}

export interface AiChatResponse {
  reply: string;
  tool_results: AiToolResult[] | null;
  topology_action: AiTopologyAction | null;
  scenario_action: AiScenarioAction | null;
}

const AI_BASE = '/api/ai';

export function aiChat(
  topologyId: string | null,
  messages: AiChatMessage[],
  signal?: AbortSignal,
): Promise<AiChatResponse> {
  return request<AiChatResponse>(`${AI_BASE}/chat`, {
    method: 'POST',
    signal,
    ...json({ topology_id: topologyId, messages }),
  });
}

export function aiHealth(): Promise<{ status: string; model?: string; error?: string }> {
  return request(`${AI_BASE}/health`);
}

// ── Packet Capture (Wireshark) ───────────────────────────────────

export function startCapture(
  topologyId: string,
  containerId: string,
): Promise<{ status: string; url: string }> {
  return request(`${BASE}/${topologyId}/capture/${containerId}/start`, { method: 'POST' });
}

export function stopCapture(
  topologyId: string,
  containerId: string,
): Promise<{ status: string }> {
  return request(`${BASE}/${topologyId}/capture/${containerId}/stop`, { method: 'POST' });
}

export function getCaptureStatus(
  topologyId: string,
  containerId: string,
): Promise<{ active: boolean; port?: number }> {
  return request(`${BASE}/${topologyId}/capture/${containerId}/status`);
}

export function checkCaptureReady(
  topologyId: string,
  containerId: string,
): Promise<{ ready: boolean }> {
  return request(`${BASE}/${topologyId}/capture/${containerId}/ready`);
}

export async function downloadPcap(
  topologyId: string,
  containerId: string,
): Promise<void> {
  const url = `${BASE}/${topologyId}/capture/${containerId}/download`;
  const headers: Record<string, string> = {};
  if (_authToken) headers['Authorization'] = `Bearer ${_authToken}`;
  const resp = await fetch(url, { headers });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Download failed (${resp.status})`);
  }
  const blob = await resp.blob();
  const disposition = resp.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] || 'capture.pcapng';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── Presets ──────────────────────────────────────────────────────

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

export function loadPreset(
  presetId: string,
): Promise<{ id: string; name: string; status: string; created_at: string }> {
  return request(`${PRESETS}/${presetId}/load`, { method: 'POST' });
}
