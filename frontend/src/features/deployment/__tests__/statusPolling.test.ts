import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAppStore } from '@/store';

vi.mock('@/api/client', async (orig) => {
  const real = await orig<typeof import('@/api/client')>();
  return { ...real, getRuntime: vi.fn(), getJob: vi.fn() };
});
vi.mock('../actions', () => ({ refreshFromServer: vi.fn() }));

import * as api from '@/api/client';
import { refreshFromServer } from '../actions';
import { startPolling, stopPolling } from '../statusPolling';

const S = () => useAppStore.getState();

beforeEach(() => {
  vi.mocked(refreshFromServer).mockReset();
  S().setBackendInfo({ id: 'topo-1', name: 'Lab', status: 'deployed', version: 1 });
});
afterEach(() => stopPolling());

describe('status polling', () => {
  it('takes a newer saved version instead of just adopting its number', async () => {
    vi.mocked(api.getRuntime).mockResolvedValue({
      topology_id: 'topo-1',
      status: 'deployed',
      version: 2,
      active_job: null,
      activity: [],
      nodes: [],
      saved: null,
      deployed_at: null,
    } as unknown as api.Runtime);
    startPolling('topo-1');
    await vi.waitFor(() => expect(refreshFromServer).toHaveBeenCalledWith('topo-1'));
    // Our version stays until the record is actually taken, so a save with
    // unsaved edits still reports the conflict.
    expect(S().version).toBe(1);
  });
});
