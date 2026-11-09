// Save / load / deploy / destroy / export. Plain functions over the store so
// any component (top bar, command palette, hotkeys) can call them.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { toast } from '@/ui';
import { startPolling, stopPolling } from './statusPolling';

async function withBusy<T>(fn: () => Promise<T>): Promise<T> {
  useAppStore.getState().setBusy(true);
  try {
    return await fn();
  } finally {
    useAppStore.getState().setBusy(false);
  }
}

function applyRecord(rec: api.TopologyRecord) {
  const st = useAppStore.getState();
  st.setBackendInfo({ id: rec.id, name: rec.name, status: rec.status, version: rec.version });
  st.setDiagnostics(rec.diagnostics ?? []);
  st.setSavedState(rec.saved ?? null);
  st.setRecordMeta({
    owner: rec.owner ?? null,
    published: rec.published ?? false,
    sourceId: rec.source_id ?? null,
    updateAvailable: rec.update_available ?? false,
  });
}

/** A student opening someone else's (published) topology works on their own
 *  copy of it; everyone else opens the topology itself. */
function isOthersForStudent(rec: api.TopologyRecord): boolean {
  const user = useAppStore.getState().user;
  return user?.role === 'student' && rec.owner?.id !== user.id;
}

/** Save the current topology; returns its backend id (assigned on first save) or null on failure. */
export async function saveTopology(name?: string): Promise<string | null> {
  return withBusy(async () => {
    const s = useAppStore.getState();
    const displayName = name || s.topology.name || s.backendName || 'Untitled topology';
    try {
      const rec = s.backendId
        ? await api.updateTopology(s.backendId, { name: displayName, data: s.topology, version: s.version })
        : await api.createTopology(displayName, s.topology);
      applyRecord(rec);
      const st = useAppStore.getState();
      if (st.topology.name !== rec.name) st.setTopologyMeta({ name: rec.name });
      st.markClean();
      const errors = (rec.diagnostics ?? []).filter((d) => d.severity === 'error').length;
      toast.success('Saved', { description: errors ? `${rec.name} · ${errors} issue${errors === 1 ? '' : 's'} to fix before deploying` : rec.name, duration: 1800 });
      return rec.id;
    } catch (err) {
      if (err instanceof api.ApiError && err.code === 'version_conflict' && s.backendId) {
        const id = s.backendId;
        toast.error('Changed elsewhere', {
          description: 'This topology was saved by someone else since you loaded it.',
          duration: 10000,
          action: { label: 'Reload', onClick: () => void loadTopology(id) },
        });
        return null;
      }
      toast.error('Save failed', { description: api.errorMessage(err) });
      return null;
    }
  });
}

/** Load a topology into the editor; returns the id actually loaded (a student
 *  opening a published topology gets their copy's), or null on failure. */
export async function loadTopology(id: string): Promise<string | null> {
  return withBusy(async () => {
    try {
      let rec = await api.getTopology(id);
      if (isOthersForStudent(rec)) rec = await api.copyTopology(rec.id);
      const s = useAppStore.getState();
      stopPolling();
      s.clearSelection();
      s.collapseAll();
      if (s.backendId !== rec.id) s.resetTutorialSession();
      s.loadTopology(rec.data);
      applyRecord(rec);
      s.clearContainerStatuses();
      s.setActiveJob(null);
      if (rec.status !== 'idle') startPolling(rec.id);
      return rec.id;
    } catch (err) {
      toast.error('Could not load topology', { description: api.errorMessage(err) });
      return null;
    }
  });
}

export async function deployTopology(): Promise<void> {
  const s = useAppStore.getState();
  if (!s.backendId) return;
  if (s.dirty && !(await saveTopology())) return;
  const id = s.backendId;
  await withBusy(async () => {
    try {
      const job = await api.deployTopology(id);
      const st = useAppStore.getState();
      st.setDeployStatus('deploying');
      st.setActiveJob(job);
      startPolling(id);
    } catch (err) {
      if (err instanceof api.ApiError && err.code === 'validation_failed') {
        const diags = (err.data.diagnostics as api.Diagnostic[] | undefined) ?? [];
        useAppStore.getState().setDiagnostics(diags);
        const errors = diags.filter((d) => d.severity === 'error').length;
        toast.error('Fix the design first', { description: `${errors} error${errors === 1 ? '' : 's'} listed under Issues in the inspector.` });
        return;
      }
      if (err instanceof api.ApiError && err.code === 'lab_limit') {
        toast.error('Lab limit reached', { description: err.message, duration: 10000 });
        return;
      }
      toast.error('Deploy failed', { description: api.errorMessage(err) });
    }
  });
}

/** Replace this copy's design with its source's latest (classroom mode). The
 *  lab must be down; edits made to the copy are lost. */
export async function resetToSource(): Promise<boolean> {
  const s = useAppStore.getState();
  if (!s.backendId) return false;
  const id = s.backendId;
  return withBusy(async () => {
    try {
      const rec = await api.resetTopology(id);
      const st = useAppStore.getState();
      stopPolling();
      st.clearSelection();
      st.loadTopology(rec.data);
      applyRecord(rec);
      toast.success('Reset to the latest version', { description: rec.name });
      return true;
    } catch (err) {
      toast.error('Could not reset', { description: api.errorMessage(err) });
      return false;
    }
  });
}

/** Ask how to stop the lab: keep it running, save & destroy, or destroy. */
export function requestDestroy(): void {
  useAppStore.getState().setDestroyDialogOpen(true);
}

/** `save`: commit every node first so the next deploy resumes where it left off. */
export async function destroyTopology(opts: { save?: boolean } = {}): Promise<void> {
  const s = useAppStore.getState();
  if (!s.backendId) return;
  const id = s.backendId;
  await withBusy(async () => {
    try {
      const job = await api.destroyTopology(id, opts);
      const st = useAppStore.getState();
      st.setDeployStatus('destroying');
      st.setActiveJob(job);
      startPolling(id);
    } catch (err) {
      toast.error('Destroy failed', { description: api.errorMessage(err) });
    }
  });
}

/** Forget the saved lab state (removes its images). */
export async function discardSavedState(): Promise<boolean> {
  const s = useAppStore.getState();
  if (!s.backendId) return false;
  const id = s.backendId;
  return withBusy(async () => {
    try {
      await api.discardSavedState(id);
      useAppStore.getState().setSavedState(null);
      return true;
    } catch (err) {
      toast.error('Could not discard the saved state', { description: api.errorMessage(err) });
      return false;
    }
  });
}

/** Deploy from the catalog images, discarding the saved state first. */
export async function deployFresh(): Promise<void> {
  if (await discardSavedState()) await deployTopology();
}

/** Start an unsaved draft in the editor. */
export function createNewTopology(name?: string): void {
  const s = useAppStore.getState();
  stopPolling();
  s.clearSelection();
  s.collapseAll();
  s.clearBackend();
  s.resetTutorialSession();
  s.newTopology(name);
}

/** The design file as the editor sees it (frontend JSON, re-importable). */
export function exportDesignJson(): void {
  const s = useAppStore.getState();
  const name = s.topology.name || s.backendName || 'topology';
  const payload = { name, description: s.topology.description ?? 'Exported from AE3GIS.', topology: s.topology };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${name.replace(/[^\w.-]+/g, '_')}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

/** Server-rendered lab representations (need a saved topology). */
export async function exportLab(format: api.ExportFormat): Promise<void> {
  const s = useAppStore.getState();
  if (!s.backendId) { toast.info('Save the topology first.'); return; }
  try {
    await api.downloadExport(s.backendId, format);
  } catch (err) {
    toast.error('Export failed', { description: api.errorMessage(err) });
  }
}

export const exportTopologyJson = exportDesignJson;
