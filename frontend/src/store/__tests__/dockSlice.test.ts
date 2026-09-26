import { beforeEach, describe, expect, it } from 'vitest';
import { useAppStore } from '@/store';

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
});
