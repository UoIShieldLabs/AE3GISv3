import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAppStore } from '@/store';
import type { TopologyData } from '@/types/topology';

vi.mock('@/api/client', async (orig) => {
  const real = await orig<typeof import('@/api/client')>();
  return { ...real, getTopology: vi.fn() };
});
vi.mock('@/features/deployment/statusPolling', () => ({ startPolling: vi.fn(), stopPolling: vi.fn() }));

import * as api from '@/api/client';
import { startPolling } from '@/features/deployment/statusPolling';
import { refreshFromServer } from '@/features/deployment/actions';
import { handleUiAction, setAgentNavigator } from '../uiActions';

const S = () => useAppStore.getState();
const RUN = { jobId: 'job-1', chatId: 'chat-1' };

const DATA: TopologyData = {
  name: 'Lab',
  sites: [
    {
      id: 's1',
      name: 'Site',
      location: '',
      position: { x: 0, y: 0 },
      subnets: [{ id: 'n1', name: 'LAN', cidr: '10.0.0.0/24', containers: [{ id: 'h1', name: 'Host', type: 'workstation', ip: '10.0.0.5', position: { x: 0, y: 0 } }], connections: [] }],
      subnetConnections: [],
    },
  ],
  siteConnections: [],
};

function openTopology(version = 1) {
  S().loadTopology(DATA);
  S().setBackendInfo({ id: 'topo-1', name: 'Lab', status: 'deployed', version });
}

function record(version: number, data: TopologyData): api.TopologyRecord {
  return { id: 'topo-1', name: 'Lab', status: 'deployed', version, data, diagnostics: [] } as unknown as api.TopologyRecord;
}

beforeEach(() => {
  vi.mocked(api.getTopology).mockReset();
  vi.mocked(startPolling).mockReset();
  S().setAgentLock(null);
  S().clearBackend();
  S().closeTerminal('h1');
});

describe('handleUiAction', () => {
  it('navigates to an opened topology and moves the lock there', () => {
    const go = vi.fn();
    setAgentNavigator(go);
    S().setAgentLock({ topologyId: 'old', chatId: 'chat-1', jobId: 'job-1' });
    handleUiAction({ type: 'open_topology', topology_id: 'topo-9', site_id: 's1' }, RUN);
    expect(go).toHaveBeenCalledWith('/t/topo-9/site/s1');
    expect(S().agentLock?.topologyId).toBe('topo-9');
  });

  it("never takes another run's lock", () => {
    S().setAgentLock({ topologyId: 'x', chatId: 'other', jobId: 'job-2' });
    handleUiAction({ type: 'topology_changed', topology_id: 'topo-1', version: 2 }, RUN);
    expect(S().agentLock?.jobId).toBe('job-2');
  });

  it('reloads the open topology the agent changed, as an undo step', async () => {
    openTopology(1);
    const changed: TopologyData = { ...DATA, sites: [{ ...DATA.sites[0], name: 'Renamed by agent' }] };
    vi.mocked(api.getTopology).mockResolvedValue(record(2, changed));
    handleUiAction({ type: 'topology_changed', topology_id: 'topo-1', version: 2 }, RUN);
    await vi.waitFor(() => expect(S().topology.sites[0].name).toBe('Renamed by agent'));
    expect(S().version).toBe(2);
    expect(S().dirty).toBe(false);
  });

  it('opens a terminal on a device and starts polling after a deploy', () => {
    openTopology();
    handleUiAction({ type: 'open_view', topology_id: 'topo-1', view: 'terminal', node: 'h1' }, RUN);
    expect(S().dockTabs.some((t) => t.kind === 'terminal' && t.containerId === 'h1')).toBe(true);
    handleUiAction({ type: 'runtime_changed', topology_id: 'topo-1' }, RUN);
    expect(startPolling).toHaveBeenCalledWith('topo-1');
  });

  it('ignores actions about a topology that is not open', () => {
    openTopology();
    handleUiAction({ type: 'select', topology_id: 'elsewhere', ids: ['h1'] }, RUN);
    expect(S().selection.nodeIds).toEqual([]);
    handleUiAction({ type: 'select', topology_id: 'topo-1', ids: ['h1'] }, RUN);
    expect(S().selection.nodeIds).toEqual(['h1']);
  });
});

describe('refreshFromServer', () => {
  it('never overwrites unsaved edits', async () => {
    openTopology(1);
    S().addSite({ name: 'Unsaved' });
    const ok = await refreshFromServer('topo-1', { notifyIfDirty: false });
    expect(ok).toBe(false);
    expect(api.getTopology).not.toHaveBeenCalled();
    expect(S().topology.sites.map((s) => s.name)).toContain('Unsaved');
  });
});
