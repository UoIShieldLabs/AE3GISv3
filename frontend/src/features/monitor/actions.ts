// Monitor actions shared by the canvas menu, the inspector, the palette and the dock.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { monitorTabId } from '@/store/slices/dockSlice';
import { startPolling } from '@/features/deployment/statusPolling';
import { toast } from '@/ui';

/** Open the "new monitor" form (optionally with nodes picked). */
export function openMonitorPanel(seed: { nodes?: string[] } = {}) {
  useAppStore.getState().openDockTab({ kind: 'monitor', id: monitorTabId(null), jobId: null, title: 'New monitor', seed: { ...seed, nonce: Date.now() } });
}

export function openMonitor(jobId: string, title = 'Monitor') {
  useAppStore.getState().openDockTab({ kind: 'monitor', id: monitorTabId(jobId), jobId, title });
}

/** Start a monitor; the form's tab becomes its live view. */
export async function startMonitor(fromTabId: string, body: api.MonitorRequest): Promise<api.Monitor | null> {
  const id = useAppStore.getState().backendId;
  if (!id) return null;
  try {
    const mon = await api.startMonitor(id, body);
    useAppStore.getState().replaceDockTab(fromTabId, { kind: 'monitor', id: monitorTabId(mon.id), jobId: mon.id, title: mon.label || 'Monitor' });
    startPolling(id);
    return mon;
  } catch (err) {
    const running = err instanceof api.ApiError && err.code === 'monitor_active' ? String(err.data.job_id ?? '') : '';
    toast.error('Could not start the monitor', {
      description: api.errorMessage(err),
      action: running ? { label: 'Show it', onClick: () => openMonitor(running) } : undefined,
    });
    return null;
  }
}

export async function stopMonitor(jobId: string): Promise<void> {
  try {
    await api.stopJob(jobId);
    const id = useAppStore.getState().backendId;
    if (id) startPolling(id);
  } catch (err) {
    toast.error('Could not stop the monitor', { description: api.errorMessage(err) });
  }
}

export function exportMonitor(jobId: string) {
  api.downloadUrl(api.monitorExportUrl(jobId), `monitor-${jobId.slice(0, 8)}.zip`).catch((err: unknown) =>
    toast.error('Export failed', { description: api.errorMessage(err) }),
  );
}
