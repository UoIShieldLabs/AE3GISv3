// All REST/WebSocket calls to the backend. Types come from the backend's
// OpenAPI document (npm run api:types -> ./schema.d.ts), so the backend is the
// typed source of truth for the API; only `TopologyData` is frontend-owned.
import type { components } from './schema';
import type { TopologyData } from '../types/topology';
import { getToken, notifyUnauthorized } from './session';

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
export type SavedState = S['SavedStateOut'];
export type TopologyEvent = S['EventOut'];
export type PlanOut = S['PlanOut'];
export type LabsReport = S['LabsReport'];
export type Lab = S['LabOut'];
export type Health = S['HealthOut'];
export type PresetSummary = S['PresetSummary'];
export type ContextOut = S['ContextOut'];
export type Catalog = S['Catalog'];
export type JobLog = S['JobLogOut'];
export type ImagesReport = S['ImagesReport'];
export type ImageStatus = S['ImageStatusOut'];
export type ImageSource = S['SourceOut'];
export type Registry = S['RegistryOut'];
export type RegistryImage = S['RegistryImageOut'];
export type Activity = S['ActivityOut'];
export type Artifact = S['ArtifactOut'];
export type DeployedInterfaces = S['DeployedInterfacesOut'];
export type DeployedInterface = S['InterfaceOut'];
export type CaptureRequest = S['CaptureRequest'];
export type Capture = S['CaptureOut'];
export type PacketSummary = S['PacketSummaryOut'];
export type PacketPage = S['PacketPageOut'];
export type TrafficRunRequest = S['TrafficRunRequest'];
export type Iperf3Flow = S['Iperf3Flow'];
export type TrafficRun = S['TrafficRunOut'];
export type FlowSample = S['FlowSampleOut'];
export type TrafficTotals = S['TrafficTotalsOut'];
export type TrafficPattern = S['TrafficPattern'];
export type TrafficSamples = S['TrafficSamplesOut'];
export type ScenarioStepRequest = S['ScenarioStepRequest'];
export type ScenarioRun = S['ScenarioRunOut'];
export type ScenarioStepResult = S['ScenarioStepResult'];
export type ScenarioSamples = S['ScenarioSamplesOut'];
export type MonitorRequest = S['MonitorRequest'];
export type Monitor = S['MonitorOut'];
export type NodeSelector = S['NodeSelector'];
export type MonitorSamples = S['MonitorSamplesOut'];
export type SessionUser = S['UserOut'];
export type SignIn = S['SessionOut'];
export type Me = S['MeOut'];
export type Owner = S['OwnerOut'];
export type ClassSettings = S['ClassSettingsOut'];
export type Student = S['StudentOut'];
export type Students = S['StudentsOut'];

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
// With accounts off (the default) the backend needs no token. In classroom
// mode the sign-in's token (api/session.ts) rides every request: as a bearer
// header, and as `?token=` on WebSocket and plain-link URLs (GET only).

/** WebSocket URL with the session token as a query param (browsers can't set
 *  headers on WS upgrades). */
export function wsUrl(path: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const base = `${protocol}//${window.location.host}${path}`;
  const token = getToken();
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}

// ── Transport ──────────────────────────────────────────────────────
const V1 = '/api/v1';

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
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
  if (!res.ok) {
    const err = await toApiError(res);
    // "Sign in required" (not e.g. a wrong password on the login form).
    if (err.status === 401 && err.code === 'unauthorized') notifyUnauthorized();
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function json(body: unknown, method = 'POST'): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

// ── Accounts (classroom mode) ──────────────────────────────────────
export function login(username: string, password: string): Promise<SignIn> {
  return request(`${V1}/auth/login`, json({ username, password }));
}
export function signup(username: string, password: string, joinCode: string): Promise<SignIn> {
  return request(`${V1}/auth/signup`, json({ username, password, join_code: joinCode }));
}
export function logout(): Promise<void> {
  return request(`${V1}/auth/logout`, { method: 'POST' });
}
export function getMe(): Promise<Me> {
  return request(`${V1}/auth/me`);
}
export function changePassword(current: string, next: string): Promise<void> {
  return request(`${V1}/auth/password`, json({ current, new: next }));
}
/** Let a node web-UI iframe authenticate (it cannot send a header): sets a
 *  cookie only the relay accepts. Call before showing one. */
export function issueWebUiCookie(): Promise<void> {
  return request(`${V1}/auth/webui-cookie`, { method: 'POST' });
}
export function getClassSettings(): Promise<ClassSettings> {
  return request(`${V1}/class`);
}
export function updateClassSettings(patch: { signup_open?: boolean; rotate_join_code?: boolean }): Promise<ClassSettings> {
  return request(`${V1}/class`, json(patch, 'PUT'));
}
export function listStudents(): Promise<Students> {
  return request(`${V1}/class/students`);
}
export function resetStudentPassword(userId: string): Promise<{ password: string }> {
  return request(`${V1}/class/students/${encodeURIComponent(userId)}/reset-password`, { method: 'POST' });
}
export function removeStudent(userId: string): Promise<void> {
  return request(`${V1}/class/students/${encodeURIComponent(userId)}`, { method: 'DELETE' });
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
/** A copy for the caller: a student's personal copy of a published topology
 *  (the one they already have, if any), else a duplicate they own. */
export function copyTopology(id: string): Promise<TopologyRecord> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/copy`, { method: 'POST' });
}
/** Replace a copy's design with its source's latest (the lab must be down). */
export function resetTopology(id: string): Promise<TopologyRecord> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/reset`, { method: 'POST' });
}
/** Publish a topology to students, or stop (instructor). */
export function setPublished(id: string, published: boolean): Promise<TopologyRecord> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/published`, json({ published }, 'PUT'));
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

/** Fetch a file from the API and hand it to the browser as a download
 *  (named by the server's Content-Disposition, else `fallbackName`). */
export async function downloadUrl(url: string, fallbackName: string): Promise<void> {
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) {
    const err = await toApiError(res);
    if (err.status === 401 && err.code === 'unauthorized') notifyUnauthorized();
    throw err;
  }
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition') ?? '';
  const match = /filename="?([^";]+)"?/.exec(disposition);
  const a = document.createElement('a');
  const href = URL.createObjectURL(blob);
  a.href = href;
  a.download = match?.[1] ?? fallbackName;
  a.click();
  URL.revokeObjectURL(href);
}

/** Fetch an export and hand it to the browser as a download. */
export function downloadExport(id: string, format: ExportFormat): Promise<void> {
  return downloadUrl(
    `${V1}/topologies/${encodeURIComponent(id)}/export?format=${format}`,
    `topology.${format === 'labspec' ? 'json' : 'zip'}`,
  );
}

// ── Deployment (jobs) ──────────────────────────────────────────────
export function deployTopology(id: string): Promise<Job> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/deploy`, { method: 'POST' });
}
/** `save`: commit every node's filesystem first; the next deploy resumes from it. */
export function destroyTopology(id: string, opts: { save?: boolean } = {}): Promise<Job> {
  const q = opts.save ? '?save=true' : '';
  return request(`${V1}/topologies/${encodeURIComponent(id)}/destroy${q}`, { method: 'POST' });
}
/** Forget a topology's saved lab state: the next deploy starts fresh. */
export function discardSavedState(id: string): Promise<void> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/saved-state`, { method: 'DELETE' });
}
export function getRuntime(id: string): Promise<Runtime> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/runtime`);
}
export function getJob(jobId: string): Promise<Job> {
  return request(`${V1}/jobs/${encodeURIComponent(jobId)}`);
}
/** A line-aligned slice of a job's log; omit `offset` to read the tail. */
export function getJobLog(jobId: string, offset?: number, limit?: number): Promise<JobLog> {
  const q = new URLSearchParams();
  if (offset !== undefined) q.set('offset', String(offset));
  if (limit !== undefined) q.set('limit', String(limit));
  const qs = q.toString();
  return request(`${V1}/jobs/${encodeURIComponent(jobId)}/log${qs ? `?${qs}` : ''}`);
}
export function cancelJob(jobId: string): Promise<Job> {
  return request(`${V1}/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' });
}
/** Stop an open-ended job (capture, traffic run): it keeps what it recorded. */
export function stopJob(jobId: string): Promise<Job> {
  return request(`${V1}/jobs/${encodeURIComponent(jobId)}/stop`, { method: 'POST' });
}
export function listArtifacts(jobId: string): Promise<Artifact[]> {
  return request(`${V1}/jobs/${encodeURIComponent(jobId)}/artifacts`);
}
/** A JSON artifact of a job (e.g. a run's run.json). */
export function getArtifactJson<T>(jobId: string, name: string): Promise<T> {
  return request(artifactUrl(jobId, name));
}
export function artifactUrl(jobId: string, name: string): string {
  return `${V1}/jobs/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(name)}`;
}
/** The deployed lab's interfaces (what captures can target). */
export function getInterfaces(id: string): Promise<DeployedInterfaces> {
  return request(`${V1}/topologies/${encodeURIComponent(id)}/interfaces`);
}
export function execWsPath(id: string, containerId: string): string {
  return `${V1}/topologies/ws/${encodeURIComponent(id)}/exec/${encodeURIComponent(containerId)}`;
}

// ── Images ─────────────────────────────────────────────────────────
/** Build support, image sources, and the status of every catalog image
 *  (or only those a topology uses). */
export function getImages(topologyId?: string): Promise<ImagesReport> {
  return request(`${V1}/images${topologyId ? `?topology_id=${encodeURIComponent(topologyId)}` : ''}`);
}
/** Start builds (an image already building returns its running job). */
export function buildImages(refs: string[], fresh = false): Promise<Job[]> {
  return request(`${V1}/images/builds`, json({ refs, fresh }));
}
export function syncSource(name: string): Promise<Job> {
  return request(`${V1}/sources/${encodeURIComponent(name)}/sync`, { method: 'POST' });
}

// ── Registries (Docker Hub namespaces whose standard images join the catalog)
/** Add a namespace by Docker Hub URL or name; its first sync starts right away. */
export function addRegistry(url: string): Promise<Registry> {
  return request(`${V1}/registries`, json({ url }));
}
export function syncRegistry(id: string): Promise<Job> {
  return request(`${V1}/registries/${encodeURIComponent(id)}/sync`, { method: 'POST' });
}
export function removeRegistry(id: string): Promise<void> {
  return request(`${V1}/registries/${encodeURIComponent(id)}`, { method: 'DELETE' });
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

// ── Packet capture ─────────────────────────────────────────────────
/** Start a capture (or get the one already running on that interface). */
export function startCapture(topologyId: string, body: CaptureRequest): Promise<Capture> {
  return request(`${V1}/topologies/${encodeURIComponent(topologyId)}/captures`, json(body));
}
export function listCaptures(topologyId: string, limit = 50): Promise<Capture[]> {
  return request(`${V1}/topologies/${encodeURIComponent(topologyId)}/captures?limit=${limit}`);
}
export function getCapture(jobId: string): Promise<Capture> {
  return request(`${V1}/captures/${encodeURIComponent(jobId)}`);
}
export function getPackets(jobId: string, after = 0, limit = 500): Promise<PacketPage> {
  return request(`${V1}/captures/${encodeURIComponent(jobId)}/packets?after=${after}&limit=${limit}`);
}
/** Absolute URL of a capture's pcap; `follow` streams it live (for Wireshark).
 *  With auth on, the token goes in the query so a pasted curl command works. */
export function pcapUrl(jobId: string, follow = false): string {
  const q = new URLSearchParams();
  if (follow) q.set('follow', 'true');
  const token = getToken();
  if (token) q.set('token', token);
  const qs = q.toString();
  return `${window.location.origin}${V1}/captures/${encodeURIComponent(jobId)}/pcap${qs ? `?${qs}` : ''}`;
}

// ── Traffic ────────────────────────────────────────────────────────
export function startTrafficRun(topologyId: string, body: TrafficRunRequest): Promise<TrafficRun> {
  return request(`${V1}/topologies/${encodeURIComponent(topologyId)}/traffic/runs`, json(body));
}
export function listTrafficRuns(topologyId: string, limit = 50): Promise<TrafficRun[]> {
  return request(`${V1}/topologies/${encodeURIComponent(topologyId)}/traffic/runs?limit=${limit}`);
}
export function getTrafficRun(jobId: string): Promise<TrafficRun> {
  return request(`${V1}/traffic/runs/${encodeURIComponent(jobId)}`);
}
export function trafficExportUrl(jobId: string): string {
  return `${V1}/traffic/runs/${encodeURIComponent(jobId)}/export`;
}

// ── Scenario runner ────────────────────────────────────────────────
export function runScenarioStep(topologyId: string, body: ScenarioStepRequest): Promise<ScenarioRun> {
  return request(`${V1}/topologies/${encodeURIComponent(topologyId)}/scenario/steps/run`, json(body));
}
export function runScenarioPhase(topologyId: string, phaseId: string, label = ''): Promise<ScenarioRun> {
  return request(
    `${V1}/topologies/${encodeURIComponent(topologyId)}/scenario/phases/${encodeURIComponent(phaseId)}/run`,
    json({ label }),
  );
}
export function listScenarioRuns(topologyId: string, limit = 50): Promise<ScenarioRun[]> {
  return request(`${V1}/topologies/${encodeURIComponent(topologyId)}/scenario/runs?limit=${limit}`);
}
export function getScenarioRun(jobId: string): Promise<ScenarioRun> {
  return request(`${V1}/scenario/runs/${encodeURIComponent(jobId)}`);
}
export function scenarioSamples(jobId: string): Promise<ScenarioSamples> {
  return request(`${V1}/scenario/runs/${encodeURIComponent(jobId)}/samples`);
}
export function scenarioExportUrl(jobId: string): string {
  return `${V1}/scenario/runs/${encodeURIComponent(jobId)}/export`;
}

// ── Monitors ───────────────────────────────────────────────────────
export function startMonitor(topologyId: string, body: MonitorRequest): Promise<Monitor> {
  return request(`${V1}/topologies/${encodeURIComponent(topologyId)}/monitors`, json(body));
}
export function listMonitors(topologyId: string, limit = 50): Promise<Monitor[]> {
  return request(`${V1}/topologies/${encodeURIComponent(topologyId)}/monitors?limit=${limit}`);
}
export function getMonitor(jobId: string): Promise<Monitor> {
  return request(`${V1}/monitors/${encodeURIComponent(jobId)}`);
}
/** Recorded sweeps; `every` keeps every n-th one (long monitors). */
export function monitorSamples(jobId: string, opts: { since?: number; nodes?: string[]; every?: number; hostOnly?: boolean } = {}): Promise<MonitorSamples> {
  const q = new URLSearchParams();
  if (opts.hostOnly) q.set('host_only', 'true');
  if (opts.since !== undefined) q.set('since', String(opts.since));
  if (opts.nodes?.length) q.set('nodes', opts.nodes.join(','));
  if (opts.every && opts.every > 1) q.set('every', String(opts.every));
  const qs = q.toString();
  return request(`${V1}/monitors/${encodeURIComponent(jobId)}/samples${qs ? `?${qs}` : ''}`);
}
export function monitorExportUrl(jobId: string): string {
  return `${V1}/monitors/${encodeURIComponent(jobId)}/export`;
}

// ── Live channels (WebSocket paths; open with `wsUrl`) ─────────────
export function captureWsPath(topologyId: string, jobId: string): string {
  return `${V1}/topologies/ws/${encodeURIComponent(topologyId)}/captures/${encodeURIComponent(jobId)}`;
}
export function trafficWsPath(topologyId: string, jobId: string): string {
  return `${V1}/topologies/ws/${encodeURIComponent(topologyId)}/traffic/${encodeURIComponent(jobId)}`;
}
export function monitorWsPath(topologyId: string, jobId: string): string {
  return `${V1}/topologies/ws/${encodeURIComponent(topologyId)}/monitors/${encodeURIComponent(jobId)}`;
}
/** Relay URL for a node's own web UI (an iframe src). Served through the same
 *  /api proxy, so it works in dev and prod without a host port. */
export function webUiUrl(topologyId: string, nodeId: string): string {
  return `${V1}/topologies/${encodeURIComponent(topologyId)}/webui/${encodeURIComponent(nodeId)}/`;
}
export function scenarioWsPath(topologyId: string, jobId: string): string {
  return `${V1}/topologies/ws/${encodeURIComponent(topologyId)}/scenario/${encodeURIComponent(jobId)}`;
}
