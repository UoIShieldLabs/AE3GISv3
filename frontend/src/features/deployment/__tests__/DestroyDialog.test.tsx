import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { TooltipProvider } from '@/ui';
import { DestroyDialog } from '../DestroyDialog';

vi.mock('../statusPolling', () => ({ startPolling: vi.fn(), stopPolling: vi.fn() }));

const JOB = { id: 'j1', kind: 'destroy', status: 'queued', steps: [] } as unknown as api.Job;

function open() {
  useAppStore.getState().setDestroyDialogOpen(true);
  render(<TooltipProvider><DestroyDialog /></TooltipProvider>);
}

describe('DestroyDialog', () => {
  beforeEach(() => {
    useAppStore.getState().clearBackend();
    useAppStore.getState().setBackendInfo({ id: 't1', name: 'demo', status: 'deployed', version: 1 });
  });
  afterEach(() => vi.restoreAllMocks());

  it('keeps the lab running without calling the API', () => {
    const destroy = vi.spyOn(api, 'destroyTopology');
    open();
    fireEvent.click(screen.getByRole('button', { name: /Keep running/ }));
    expect(destroy).not.toHaveBeenCalled();
    expect(useAppStore.getState().destroyDialogOpen).toBe(false);
  });

  it('saves before destroying', async () => {
    const destroy = vi.spyOn(api, 'destroyTopology').mockResolvedValue(JOB);
    open();
    fireEvent.click(screen.getByRole('button', { name: /Save & destroy/ }));
    await vi.waitFor(() => expect(destroy).toHaveBeenCalledWith('t1', { save: true }));
    await vi.waitFor(() => expect(useAppStore.getState().deployStatus).toBe('destroying'));
  });

  it('destroys without saving, and says an earlier save is kept', async () => {
    const destroy = vi.spyOn(api, 'destroyTopology').mockResolvedValue(JOB);
    useAppStore.getState().setSavedState({ created_at: '2026-11-08T10:00:00Z', nodes: 3 });
    open();
    expect(screen.getByText(/earlier saved state is kept/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Destroy without saving/ }));
    await vi.waitFor(() => expect(destroy).toHaveBeenCalledWith('t1', { save: false }));
  });
});
