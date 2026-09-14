import * as api from '@/api/client';
import { useAppStore, type RuntimeStatus } from '@/store';

const INTERVAL_MS = 5000;
let timer: ReturnType<typeof setInterval> | null = null;

export function stopPolling() {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
}

/** Poll engine status for a deployed topology and mirror it into the store. One poller app-wide. */
export function startPolling(topologyId: string) {
  stopPolling();
  const poll = async () => {
    try {
      const { containers, status } = await api.getTopologyStatus(topologyId);
      const statuses: Record<string, RuntimeStatus> = {};
      for (const c of containers) {
        const s = c.state?.toLowerCase();
        statuses[c.id] = s === 'running' ? 'running' : s === 'paused' ? 'paused' : 'stopped';
      }
      const st = useAppStore.getState();
      if (st.backendId !== topologyId) { stopPolling(); return; }
      st.setContainerStatuses(statuses);
      if (status === 'idle' && st.deployStatus === 'deployed') {
        st.setDeployStatus('idle');
        st.clearContainerStatuses();
        stopPolling();
      }
    } catch {
      /* transient */
    }
  };
  void poll();
  timer = setInterval(() => void poll(), INTERVAL_MS);
}
