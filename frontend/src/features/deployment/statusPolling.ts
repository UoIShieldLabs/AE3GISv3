// One poller app-wide for GET /runtime: deployment status, the active job
// (with steps), per-node state, and running captures/traffic runs. Polls fast while a job runs, slowly while
// deployed, and stops when there is nothing to watch.
import * as api from '@/api/client';
import { useAppStore, type RuntimeStatus } from '@/store';
import { toast } from '@/ui';

const FAST_MS = 1500;
const SLOW_MS = 5000;

let timer: ReturnType<typeof setTimeout> | null = null;
let current: string | null = null;
let lastJobId: string | null = null;

export function stopPolling() {
  if (timer !== null) clearTimeout(timer);
  timer = null;
  current = null;
  lastJobId = null;
  useAppStore.getState().setActivity([]);
}

async function tick(topologyId: string) {
  if (current !== topologyId) return;
  let delay = SLOW_MS;
  try {
    const rt = await api.getRuntime(topologyId);
    const st = useAppStore.getState();
    if (st.backendId !== topologyId) { stopPolling(); return; }

    const statuses: Record<string, RuntimeStatus> = {};
    for (const n of rt.nodes) statuses[n.id] = n.state === 'running' ? 'running' : n.state === 'paused' ? 'paused' : 'stopped';
    st.setContainerStatuses(statuses);
    st.setDeployStatus(rt.status as typeof st.deployStatus, st.lastError);
    st.setActiveJob(rt.active_job ?? null);
    st.setActivity(rt.activity ?? []);
    // Captures and traffic runs: poll briskly so their badges come and go on time.
    if (rt.activity?.length) delay = FAST_MS;
    if (rt.version !== st.version) st.setVersion(rt.version);

    const job = rt.active_job;
    if (job) {
      lastJobId = job.id;
      delay = FAST_MS;
    } else if (lastJobId) {
      // The job we were watching finished: report how it ended.
      const finished = await api.getJob(lastJobId).catch(() => null);
      lastJobId = null;
      if (finished) useAppStore.getState().setLastJob(finished);
      const details = { label: 'Details', onClick: () => useAppStore.getState().setJobDetailsOpen(true) };
      if (finished?.status === 'failed') {
        useAppStore.getState().setDeployStatus(rt.status as typeof st.deployStatus, finished.error ?? 'Job failed');
        toast.error(finished.kind === 'deploy' ? 'Deploy failed' : 'Destroy failed', { description: finished.error ?? undefined, duration: 10000, action: details });
      } else if (finished?.status === 'cancelled') {
        toast.info(finished.kind === 'deploy' ? 'Deploy cancelled' : 'Destroy cancelled', { action: details });
      } else if (finished?.status === 'succeeded') {
        if (finished.kind === 'deploy') toast.success('Deployed', { description: `${rt.nodes.length} nodes running` });
        else toast.success('Destroyed', { description: 'All containers were removed.' });
      }
    }
    if (!job && rt.status !== 'deployed') { stopPolling(); return; }
  } catch {
    delay = SLOW_MS; // transient; keep trying
  }
  if (current === topologyId) timer = setTimeout(() => void tick(topologyId), delay);
}

/** Start (or restart) polling a topology's runtime. Safe to call repeatedly. */
export function startPolling(topologyId: string) {
  if (timer !== null) clearTimeout(timer);
  current = topologyId;
  timer = setTimeout(() => void tick(topologyId), 0);
}
