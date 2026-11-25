import { beforeEach, describe, expect, it, vi } from 'vitest';
import { asAgent, clearHistory, editorLocked, setLockedEditHandler, undo, useAppStore } from '../index';
import type { TopologyData } from '@/types/topology';

const S = () => useAppStore.getState();

function lockOpenTopology() {
  S().setBackendInfo({ id: 'topo-1', name: 'Lab', status: 'idle', version: 3 });
  S().setAgentLock({ topologyId: 'topo-1', chatId: 'chat-1', jobId: 'job-1' });
}

beforeEach(() => {
  S().setAgentLock(null);
  S().clearBackend();
  S().newTopology('Test');
  clearHistory();
  setLockedEditHandler(null);
});

describe('agent slice', () => {
  it('opens and closes the panel and picks a chat', () => {
    S().setAgentOpen(false);
    S().toggleAgent();
    expect(S().agentOpen).toBe(true);
    S().setAgentOpen(false);
    S().openAgentChat('chat-9');
    expect(S()).toMatchObject({ agentOpen: true, agentChatId: 'chat-9' });
    S().openAgentChat(null);
    expect(S().agentChatId).toBeNull();
  });
});

describe('the editor lock', () => {
  it('holds only while the locked topology is the open one', () => {
    expect(editorLocked()).toBe(false);
    lockOpenTopology();
    expect(editorLocked()).toBe(true);
    S().setBackendInfo({ id: 'topo-2', name: 'Other', status: 'idle', version: 1 });
    expect(editorLocked()).toBe(false);
  });

  it('refuses every topology edit and undo while locked, and says so', () => {
    const siteId = S().addSite({ name: 'Before' });
    lockOpenTopology();
    const onRefused = vi.fn();
    setLockedEditHandler(onRefused);
    const before = S().topology;
    expect(S().addSite({ name: 'Nope' })).toBeNull();
    S().updateSite(siteId, { name: 'Renamed' });
    S().deleteNodes([siteId]);
    undo();
    expect(S().topology).toBe(before);
    expect(onRefused).toHaveBeenCalledTimes(4);
  });

  it('lets the agent itself through', () => {
    lockOpenTopology();
    const id = asAgent(() => S().addSite({ name: 'By the agent' }));
    expect(typeof id).toBe('string');
    expect(S().topology.sites.map((s) => s.name)).toContain('By the agent');
  });
});

describe('applyRemoteTopology', () => {
  const remote: TopologyData = {
    name: 'Lab',
    sites: [{ id: 's1', name: 'From the agent', location: '', position: { x: 0, y: 0 }, subnets: [], subnetConnections: [] }],
    siteConnections: [],
  };

  it('takes the server copy clean, as one undoable step', () => {
    S().addSite({ name: 'Mine' });
    S().markClean();
    S().applyRemoteTopology(remote);
    expect(S().dirty).toBe(false);
    expect(S().topology.sites.map((s) => s.name)).toEqual(['From the agent']);
    undo();
    expect(S().topology.sites.map((s) => s.name)).toEqual(['Mine']);
    // Undone, the editor differs from what is saved: saving would revert it.
    expect(S().dirty).toBe(true);
  });

  it('fills what the editor needs (positions, connection ids)', () => {
    S().applyRemoteTopology({
      sites: [{ id: 's1', name: 'S', location: '', subnets: [{ id: 'n1', name: 'N', cidr: '10.0.0.0/24', containers: [{ id: 'h', name: 'h', type: 'workstation', ip: '10.0.0.5' }], connections: [] }], subnetConnections: [] }],
      siteConnections: [],
    });
    const host = S().topology.sites[0].subnets[0].containers[0];
    expect(host.position).toBeDefined();
  });
});
