// Capture actions shared by the canvas menus, the inspector and the dock.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { captureTabId } from '@/store/slices/dockSlice';
import { startPolling } from '@/features/deployment/statusPolling';
import { toast } from '@/ui';

export function openCaptureTab(jobId: string, title = 'Capture') {
  useAppStore.getState().openDockTab({ kind: 'capture', id: captureTabId(jobId), jobId, title });
}

/** Start a capture (or join the one already running there) and show it. */
export async function startCapture(body: api.CaptureRequest): Promise<api.Capture | null> {
  const id = useAppStore.getState().backendId;
  if (!id) return null;
  try {
    const cap = await api.startCapture(id, body);
    openCaptureTab(cap.id, cap.label || 'Capture');
    startPolling(id);
    return cap;
  } catch (err) {
    toast.error('Could not start the capture', { description: api.errorMessage(err) });
    return null;
  }
}

export async function stopCapture(jobId: string): Promise<void> {
  try {
    await api.stopJob(jobId);
    const id = useAppStore.getState().backendId;
    if (id) startPolling(id);
  } catch (err) {
    toast.error('Could not stop the capture', { description: api.errorMessage(err) });
  }
}

/** Download the pcap as it is now (valid even mid-capture). A plain link, so
 *  big files stream to disk instead of through memory. */
export function downloadPcap(jobId: string) {
  const a = document.createElement('a');
  a.href = api.pcapUrl(jobId);
  a.download = '';
  a.click();
}
