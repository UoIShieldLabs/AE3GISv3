import { beforeEach, describe, expect, it } from 'vitest';
import { useAppStore } from '@/store';
import type { Activity } from '@/api/client';
import { openMonitor, openMonitorPanel } from '../actions';

const monitorActivity = (jobId: string) => ({ job_id: jobId, kind: 'monitor', status: 'running', label: '', node_ids: [], connection_ids: [], started_at: '2026-01-01T00:00:00', message: null }) as unknown as Activity;

describe('monitor actions', () => {
  beforeEach(() => useAppStore.setState({ dockTabs: [], activeDockTabId: null, activity: [] }));

  it('opens the new-monitor form with the devices to pin', () => {
    openMonitorPanel({ nodes: ['h1'] });
    const tab = useAppStore.getState().dockTabs[0];
    expect(tab).toMatchObject({ kind: 'monitor', id: 'monitor:new', jobId: null, seed: { nodes: ['h1'] } });
  });

  it('pins on the running monitor instead of starting another', () => {
    useAppStore.setState({ activity: [monitorActivity('j1')] });
    openMonitor('j1', 'Baseline');
    openMonitorPanel({ nodes: ['h2'] });
    const { dockTabs, activeDockTabId } = useAppStore.getState();
    expect(dockTabs).toHaveLength(1);
    expect(dockTabs[0]).toMatchObject({ kind: 'monitor', id: 'monitor:j1', jobId: 'j1', title: 'Baseline', seed: { nodes: ['h2'] } });
    expect(activeDockTabId).toBe('monitor:j1');
  });
});
