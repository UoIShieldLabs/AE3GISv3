// Monitor actions shared by the canvas menu, the inspector, the palette and the dock.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { monitorTabId } from '@/store/slices/dockSlice';
import { startPolling } from '@/features/deployment/statusPolling';
import { toast } from '@/ui';

/** The topology's running monitor (one at a time), from /runtime's activity. */
function runningMonitorId(): string | null {
  return useAppStore.getState().activity.find((a) => a.kind === 'monitor')?.job_id ?? null;
}

/** Monitor the lab, with ``nodes`` pinned: opens the running monitor (pinning
 *  them) when there is one, else the "new monitor" form. */
export function openMonitorPanel(seed: { nodes?: string[] } = {}) {
  const running = runningMonitorId();
  if (running) {
    openMonitor(running, undefined, seed.nodes);
    return;
  }
  useAppStore.getState().openDockTab({ kind: 'monitor', id: monitorTabId(null), jobId: null, title: 'New monitor', seed: { ...seed, nonce: Date.now() } });
}

/** Open a monitor's view; ``pin`` adds devices to its pins. */
export function openMonitor(jobId: string, title?: string, pin?: string[]) {
  const s = useAppStore.getState();
  const id = monitorTabId(jobId);
  const tab = s.dockTabs.find((t) => t.id === id);
  const open = tab?.kind === 'monitor' ? tab : undefined;
  const seed = pin?.length ? { nodes: pin, nonce: Date.now() } : open?.seed;
  s.openDockTab({ kind: 'monitor', id, jobId, title: title ?? open?.title ?? 'Monitor', seed });
}

/** Start a monitor of the whole lab; the form's tab becomes its live view,
 *  with ``pins`` pinned. */
export async function startMonitor(fromTabId: string, body: api.MonitorRequest, pins: string[] = []): Promise<api.Monitor | null> {
  const id = useAppStore.getState().backendId;
  if (!id) return null;
  try {
    const mon = await api.startMonitor(id, body);
    useAppStore.getState().replaceDockTab(fromTabId, {
      kind: 'monitor',
      id: monitorTabId(mon.id),
      jobId: mon.id,
      title: mon.label || 'Monitor',
      seed: pins.length ? { nodes: pins, nonce: Date.now() } : undefined,
    });
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
