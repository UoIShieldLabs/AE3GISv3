import type { DockSlice, DockTab, SliceCreator } from '../types';

/** The bottom dock's tabs: terminals, live captures, traffic runs. */
export const createDockSlice: SliceCreator<DockSlice> = (set) => ({
  dockTabs: [],
  activeDockTabId: null,
  dockMinimized: false,

  openDockTab: (tab: DockTab) =>
    set((s) => {
      const i = s.dockTabs.findIndex((t) => t.id === tab.id);
      if (i === -1) s.dockTabs.push(tab);
      else s.dockTabs[i] = tab;
      s.activeDockTabId = tab.id;
      s.dockMinimized = false;
    }, false, 'openDockTab'),

  replaceDockTab: (id, tab) =>
    set((s) => {
      // Drop any other tab that already has the new id, then swap in place.
      const tabs = s.dockTabs.filter((t) => t.id === id || t.id !== tab.id);
      const i = tabs.findIndex((t) => t.id === id);
      if (i === -1) tabs.push(tab);
      else tabs[i] = tab;
      s.dockTabs = tabs;
      if (s.activeDockTabId === id || i === -1) s.activeDockTabId = tab.id;
    }, false, 'replaceDockTab'),

  closeDockTab: (id) =>
    set((s) => {
      s.dockTabs = s.dockTabs.filter((t) => t.id !== id);
      if (s.activeDockTabId === id) s.activeDockTabId = s.dockTabs.length ? s.dockTabs[s.dockTabs.length - 1].id : null;
    }, false, 'closeDockTab'),

  setActiveDockTab: (id) => set({ activeDockTabId: id, dockMinimized: false }, false, 'setActiveDockTab'),
  setDockMinimized: (dockMinimized) => set({ dockMinimized }, false, 'setDockMinimized'),

  openTerminal: (c) =>
    set((s) => {
      const id = terminalTabId(c.id);
      if (!s.dockTabs.some((t) => t.id === id)) s.dockTabs.push({ kind: 'terminal', id, containerId: c.id, name: c.name, ip: c.ip });
      s.activeDockTabId = id;
      s.dockMinimized = false;
    }, false, 'openTerminal'),

  closeTerminal: (containerId) =>
    set((s) => {
      const id = terminalTabId(containerId);
      s.dockTabs = s.dockTabs.filter((t) => t.id !== id);
      if (s.activeDockTabId === id) s.activeDockTabId = s.dockTabs.length ? s.dockTabs[s.dockTabs.length - 1].id : null;
    }, false, 'closeTerminal'),
});

export const terminalTabId = (containerId: string) => `term:${containerId}`;
export const captureTabId = (jobId: string) => `cap:${jobId}`;
export const trafficTabId = (jobId?: string | null) => (jobId ? `traffic:${jobId}` : 'traffic:new');
