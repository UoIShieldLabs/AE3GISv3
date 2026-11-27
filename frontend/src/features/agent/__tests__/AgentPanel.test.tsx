import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import type * as api from '@/api/client';

vi.mock('@/api/client', async (orig) => {
  const real = await orig<typeof import('@/api/client')>();
  return { ...real, listAgentChats: vi.fn() };
});
vi.mock('../actions', () => ({ newChat: vi.fn(), renameChat: vi.fn(), setAutoApprove: vi.fn(), openChat: vi.fn(), deleteChat: vi.fn(), sendMessage: vi.fn(), stopRun: vi.fn() }));

import * as client from '@/api/client';
import { useAppStore } from '@/store';
import { TooltipProvider } from '@/ui';
import { openChat } from '../actions';
import { useAgentStore } from '../agentStore';
import { AgentPanel } from '../AgentPanel';

const aliceChat = {
  id: 'c-alice',
  title: 'Explain how this topology is wired',
  mode: 'tutor',
  topology_id: 'topo-1',
  topology_name: 'Simple Lab',
  auto_approve: false,
  owner: { id: 'u-alice', username: 'alice' },
  created_at: '2026-11-27T10:00:00Z',
  updated_at: '2026-11-27T10:00:00Z',
  active_job_id: null,
} as unknown as api.AgentChat;

function renderPanel(path = '/t/topo-1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <TooltipProvider>
        <AgentPanel />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(client.listAgentChats).mockReset().mockResolvedValue([aliceChat]);
  vi.mocked(openChat).mockReset();
  useAgentStore.setState({
    status: { enabled: true, mode: 'full', provider: 'fake', model: 'fake-model' } as unknown as api.AgentStatus,
    chats: [],
    byId: {},
    draft: '',
    ownerChats: null,
  });
  useAppStore.setState({
    user: { id: 'u-tess', username: 'tess', role: 'instructor' } as unknown as api.SessionUser,
    agentChatId: null,
    agentListing: false,
    agentListScope: 'all',
  });
  useAppStore.getState().setBackendInfo({ id: 'topo-1', name: 'Simple Lab', status: 'idle', version: 1 });
  useAppStore.getState().setRecordMeta({ owner: { id: 'u-alice', username: 'alice' } as api.Owner, published: false, sourceId: null, updateAvailable: false });
});

describe('AgentPanel', () => {
  it('lets staff on a student’s topology open that student’s chats there', async () => {
    renderPanel();
    const view = await screen.findByRole('button', { name: /alice has 1 chat here/ });
    expect(client.listAgentChats).toHaveBeenCalledWith({ owner: 'u-alice', topologyId: 'topo-1' });
    fireEvent.click(view);
    expect(useAppStore.getState()).toMatchObject({ agentListing: true, agentListScope: 'owner' });
    expect(await screen.findByRole('tab', { name: /alice’s/ })).toHaveAttribute('aria-selected', 'true');
    fireEvent.click(screen.getByText('Explain how this topology is wired'));
    expect(openChat).toHaveBeenCalledWith('c-alice');
    // Someone else's chat can be read, not deleted.
    expect(screen.queryByRole('button', { name: 'Delete chat' })).toBeNull();
  });

  it('shows nothing extra on your own topology', async () => {
    useAppStore.getState().setRecordMeta({ owner: { id: 'u-tess', username: 'tess' } as api.Owner, published: false, sourceId: null, updateAvailable: false });
    renderPanel();
    await act(async () => {});
    expect(client.listAgentChats).not.toHaveBeenCalled();
    expect(screen.queryByText(/has 1 chat here/)).toBeNull();
  });

  it('a starter chip fills the message box without sending', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: 'Build a lab' }));
    const box = screen.getByRole('textbox', { name: 'Message the agent' });
    await waitFor(() => expect((box as HTMLTextAreaElement).value).toMatch(/^Build a lab with an IT and an OT subnet/));
  });
});
