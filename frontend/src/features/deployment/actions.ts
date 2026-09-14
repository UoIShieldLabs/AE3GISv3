// Save / load / deploy / destroy / export. Plain functions over the store so
// any component (top bar, command palette, hotkeys) can call them.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { toast } from '@/ui';
import { startPolling, stopPolling } from './statusPolling';

async function withBusy<T>(fn: () => Promise<T>): Promise<T> {
  const st = useAppStore.getState();
  st.setBusy(true);
  try {
    return await fn();
  } finally {
    useAppStore.getState().setBusy(false);
  }
}

/** Save the current topology; returns its backend id (assigned on first save) or null on failure. */
export async function saveTopology(name?: string): Promise<string | null> {
  return withBusy(async () => {
    const s = useAppStore.getState();
    const displayName = name || s.topology.name || s.backendName || 'Untitled topology';
    try {
      const rec = s.backendId
        ? await api.updateTopology(s.backendId, displayName, s.topology)
        : await api.createTopology(displayName, s.topology);
      const st = useAppStore.getState();
      st.setBackendInfo({ id: rec.id, name: rec.name, status: rec.status });
      if (st.topology.name !== rec.name) st.setTopologyMeta({ name: rec.name });
      st.markClean();
      toast.success('Saved', { description: rec.name, duration: 1800 });
      return rec.id;
    } catch (err) {
      toast.error('Save failed', { description: api.errorMessage(err) });
      return null;
    }
  });
}

export async function loadTopology(id: string): Promise<boolean> {
  return withBusy(async () => {
    try {
      const rec = await api.getTopology(id);
      const s = useAppStore.getState();
      stopPolling();
      s.clearSelection();
      s.collapseAll();
      s.loadTopology(rec.data);
      s.setBackendInfo({ id: rec.id, name: rec.name, status: rec.status });
      s.clearContainerStatuses();
      if (rec.status === 'deployed') startPolling(rec.id);
      return true;
    } catch (err) {
      toast.error('Could not load topology', { description: api.errorMessage(err) });
      return false;
    }
  });
}

export async function deployTopology(): Promise<void> {
  const s = useAppStore.getState();
  if (!s.backendId) return;
  const id = s.backendId;
  await withBusy(async () => {
    try {
      if (s.dirty) {
        await api.updateTopology(id, s.topology.name ?? undefined, s.topology);
        useAppStore.getState().markClean();
      }
      useAppStore.getState().setDeployStatus('deploying');
      await api.deployTopology(id);
      useAppStore.getState().setDeployStatus('deployed');
      startPolling(id);
      toast.success('Deployed', { description: 'Containers are starting; status refreshes every few seconds.' });
    } catch (err) {
      const msg = api.errorMessage(err);
      useAppStore.getState().setDeployStatus('error', msg);
      toast.error('Deploy failed', { description: msg });
    }
  });
}

export async function destroyTopology(): Promise<void> {
  const s = useAppStore.getState();
  if (!s.backendId) return;
  const id = s.backendId;
  await withBusy(async () => {
    try {
      useAppStore.getState().setDeployStatus('destroying');
      await api.destroyTopology(id);
      const st = useAppStore.getState();
      st.setDeployStatus('idle');
      st.clearContainerStatuses();
      stopPolling();
      toast.success('Destroyed', { description: 'All containers were removed.' });
    } catch (err) {
      const msg = api.errorMessage(err);
      useAppStore.getState().setDeployStatus('error', msg);
      toast.error('Destroy failed', { description: msg });
    }
  });
}

/** Start an unsaved draft in the editor. */
export function createNewTopology(name?: string): void {
  const s = useAppStore.getState();
  stopPolling();
  s.clearSelection();
  s.collapseAll();
  s.clearBackend();
  s.newTopology(name);
}

export function exportTopologyJson(): void {
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
