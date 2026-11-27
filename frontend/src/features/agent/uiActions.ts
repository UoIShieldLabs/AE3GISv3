// What the agent asks the browser to do (its `ui` events): open a topology,
// select devices, open a dock view, re-arrange the canvas, and reload the open
// topology when the agent changed it. Only the chat's owner's browser obeys.
import { asAgent, useAppStore } from '@/store';
import { captureTabId, monitorTabId, scenarioTabId, trafficTabId } from '@/store/slices/dockSlice';
import { scopePath, type Scope } from '@/lib/topology';
import type { LayoutMode } from '@/canvas/layout/algorithms';
import { refreshFromServer, saveTopology } from '@/features/deployment/actions';
import { startPolling } from '@/features/deployment/statusPolling';

type Navigate = (to: string) => void;
let navigateTo: Navigate = (to) => window.location.assign(to);

/** The router's navigate, registered by the agent frame (a component). */
export function setAgentNavigator(fn: Navigate) {
  navigateTo = fn;
}

export type UiAction = { type: string; topology_id?: string; [key: string]: unknown };

function scopeOf(action: UiAction): Scope {
  const siteId = typeof action.site_id === 'string' ? action.site_id : '';
  const subnetId = typeof action.subnet_id === 'string' ? action.subnet_id : '';
  if (siteId && subnetId) return { level: 'subnet', siteId, subnetId };
  if (siteId) return { level: 'site', siteId };
  return { level: 'root' };
}

/** The agent is working in this topology: lock it while the run lasts. */
function follow(topologyId: string, jobId: string, chatId: string) {
  const st = useAppStore.getState();
  // Not another chat's run: that one keeps its lock.
  if (st.agentLock && st.agentLock.jobId !== jobId) return;
  if (st.agentLock?.topologyId !== topologyId) st.setAgentLock({ topologyId, jobId, chatId });
}

export function handleUiAction(action: UiAction, run: { jobId: string; chatId: string }) {
  const st = useAppStore.getState();
  const tid = action.topology_id;
  const open = !!tid && st.backendId === tid;
  switch (action.type) {
    case 'open_topology': {
      if (!tid) return;
      follow(tid, run.jobId, run.chatId);
      navigateTo(scopePath(tid, scopeOf(action)));
      return;
    }
    case 'topology_changed': {
      if (!tid) return;
      follow(tid, run.jobId, run.chatId);
      if (open) void refreshFromServer(tid);
      return;
    }
    case 'runtime_changed':
      if (open && tid) startPolling(tid);
      return;
    case 'topology_deleted':
      if (open) navigateTo('/');
      return;
    case 'select': {
      if (!open) return;
      const ids = Array.isArray(action.ids) ? action.ids.filter((x): x is string => typeof x === 'string') : [];
      st.selectNodes(ids);
      return;
    }
    case 'open_view': {
      if (!open) return;
      const jobId = typeof action.job_id === 'string' ? action.job_id : '';
      switch (action.view) {
        case 'terminal': {
          const nodeId = typeof action.node === 'string' ? action.node : '';
          const node = findContainer(nodeId);
          if (node) st.openTerminal({ id: node.id, name: node.name, ip: node.ip || undefined });
          return;
        }
        case 'capture':
          if (jobId) st.openDockTab({ kind: 'capture', id: captureTabId(jobId), jobId, title: 'Capture' });
          return;
        case 'traffic':
          st.openDockTab({ kind: 'traffic', id: trafficTabId(jobId || null), jobId: jobId || null, title: 'Traffic' });
          return;
        case 'monitor':
          st.openDockTab({ kind: 'monitor', id: monitorTabId(jobId || null), jobId: jobId || null, title: 'Monitor' });
          return;
        case 'scenario':
          st.openDockTab({ kind: 'scenario', id: scenarioTabId(jobId || null), jobId: jobId || null, title: 'Scenario' });
          return;
      }
      return;
    }
    case 'arrange': {
      if (!open) return;
      const mode = (['tree', 'circle', 'grid', 'purdue'].includes(String(action.layout)) ? action.layout : 'tree') as LayoutMode;
      asAgent(() => st.applyLayout(scopeOf(action), mode));
      void saveTopology();
      return;
    }
  }
}

function findContainer(id: string) {
  for (const site of useAppStore.getState().topology.sites) {
    for (const subnet of site.subnets) {
      const c = subnet.containers.find((x) => x.id === id);
      if (c) return c;
    }
  }
  return null;
}
