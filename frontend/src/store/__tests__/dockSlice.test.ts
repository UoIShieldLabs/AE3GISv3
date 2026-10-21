import { beforeEach, describe, expect, it } from 'vitest';
import { useAppStore } from '@/store';
import { monitorTabId, scenarioTabId, webuiTabId } from '@/store/slices/dockSlice';

const st = () => useAppStore.getState();

describe('dock slice', () => {
  beforeEach(() => useAppStore.setState({ dockTabs: [], activeDockTabId: null, dockMinimized: false }));

  it('terminal wrappers open one tab per container and focus it', () => {
    st().setDockMinimized(true);
    st().openTerminal({ id: 'h1', name: 'Host 1', ip: '10.0.0.5' });
    st().openTerminal({ id: 'h2', name: 'Host 2' });
    st().openTerminal({ id: 'h1', name: 'Host 1' });
    expect(st().dockTabs.map((t) => t.id)).toEqual(['term:h1', 'term:h2']);
    expect(st().activeDockTabId).toBe('term:h1');
    expect(st().dockMinimized).toBe(false);
    st().closeTerminal('h1');
    expect(st().dockTabs.map((t) => t.id)).toEqual(['term:h2']);
    expect(st().activeDockTabId).toBe('term:h2');
  });

  it('mixes tab kinds and replaces the new-run form with its run', () => {
    st().openDockTab({ kind: 'capture', id: 'cap:j1', jobId: 'j1', title: 'r1 eth1' });
    st().openDockTab({ kind: 'traffic', id: 'traffic:new', jobId: null, title: 'New traffic run' });
    st().replaceDockTab('traffic:new', { kind: 'traffic', id: 'traffic:j2', jobId: 'j2', title: 'baseline' });
    expect(st().dockTabs.map((t) => t.id)).toEqual(['cap:j1', 'traffic:j2']);
    expect(st().activeDockTabId).toBe('traffic:j2');
    // Re-opening updates a tab in place rather than duplicating it.
    st().openDockTab({ kind: 'capture', id: 'cap:j1', jobId: 'j1', title: 'renamed' });
    expect(st().dockTabs).toHaveLength(2);
    expect(st().dockTabs[0]).toMatchObject({ title: 'renamed' });
    st().closeDockTab('traffic:j2');
    expect(st().activeDockTabId).toBe('cap:j1');
  });

  it('opens a monitor form with its seed and swaps in the monitor', () => {
    st().openDockTab({ kind: 'monitor', id: monitorTabId(null), jobId: null, title: 'New monitor', seed: { nodes: ['h1'], nonce: 1 } });
    expect(st().dockTabs[0]).toMatchObject({ id: 'monitor:new', seed: { nodes: ['h1'] } });
    st().replaceDockTab('monitor:new', { kind: 'monitor', id: monitorTabId('m1'), jobId: 'm1', title: 'idle' });
    expect(st().dockTabs.map((t) => t.id)).toEqual(['monitor:m1']);
    expect(st().activeDockTabId).toBe('monitor:m1');
  });
});

describe('dock slice — scenario tabs', () => {
  const S = () => useAppStore.getState();
  beforeEach(() => useAppStore.setState({ dockTabs: [], activeDockTabId: null, dockMinimized: false }));

  it('opens the authoring tab once and a separate run tab per run', () => {
    S().openDockTab({ kind: 'scenario', id: scenarioTabId(null), jobId: null, title: 'Scenarios' });
    S().openDockTab({ kind: 'scenario', id: scenarioTabId(null), jobId: null, title: 'Scenarios' });
    S().openDockTab({ kind: 'scenario', id: scenarioTabId('j9'), jobId: 'j9', title: 'Phase run' });
    expect(S().dockTabs.map((t) => t.id)).toEqual(['scenario:new', 'scenario:j9']);
    expect(S().activeDockTabId).toBe('scenario:j9');
  });
});

describe('dock slice — web UI tabs', () => {
  const S = () => useAppStore.getState();
  beforeEach(() => useAppStore.setState({ dockTabs: [], activeDockTabId: null, dockMinimized: false }));
  it('opens one web-UI tab per node and focuses it', () => {
    S().openDockTab({ kind: 'webui', id: webuiTabId('process-sim'), nodeId: 'process-sim', title: 'process-sim · web' });
    S().openDockTab({ kind: 'webui', id: webuiTabId('process-sim'), nodeId: 'process-sim', title: 'process-sim · web' });
    expect(S().dockTabs.map((t) => t.id)).toEqual(['webui:process-sim']);
    expect(S().activeDockTabId).toBe('webui:process-sim');
  });
});
