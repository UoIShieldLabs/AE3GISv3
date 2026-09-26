// Traffic actions shared by the canvas menu, the inspector, the palette and the dock.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { trafficTabId } from '@/store/slices/dockSlice';
import { startPolling } from '@/features/deployment/statusPolling';
import { toast } from '@/ui';

/** Open the "new run" form (optionally with a client picked). */
export function openTrafficPanel(seed: { client?: string } = {}) {
  useAppStore.getState().openDockTab({ kind: 'traffic', id: trafficTabId(null), jobId: null, title: 'New traffic run', seed: { ...seed, nonce: Date.now() } });
}

export function openTrafficRun(jobId: string, title = 'Traffic run') {
  useAppStore.getState().openDockTab({ kind: 'traffic', id: trafficTabId(jobId), jobId, title });
}

/** Start a run; the form's tab becomes the run's live view. */
export async function startTrafficRun(fromTabId: string, body: api.TrafficRunRequest): Promise<api.TrafficRun | null> {
  const id = useAppStore.getState().backendId;
  if (!id) return null;
  try {
    const run = await api.startTrafficRun(id, body);
    useAppStore.getState().replaceDockTab(fromTabId, { kind: 'traffic', id: trafficTabId(run.id), jobId: run.id, title: run.label || 'Traffic run' });
    startPolling(id);
    return run;
  } catch (err) {
    const running = err instanceof api.ApiError && err.code === 'traffic_active' ? String(err.data.job_id ?? '') : '';
    toast.error('Could not start the traffic run', {
      description: api.errorMessage(err),
      action: running ? { label: 'Show it', onClick: () => openTrafficRun(running) } : undefined,
    });
    return null;
  }
}

export async function stopTrafficRun(jobId: string): Promise<void> {
  try {
    await api.stopJob(jobId);
    const id = useAppStore.getState().backendId;
    if (id) startPolling(id);
  } catch (err) {
    toast.error('Could not stop the run', { description: api.errorMessage(err) });
  }
}

export function exportTrafficRun(jobId: string) {
  api.downloadUrl(api.trafficExportUrl(jobId), `traffic-${jobId.slice(0, 8)}.zip`).catch((err: unknown) =>
    toast.error('Export failed', { description: api.errorMessage(err) }),
  );
}
