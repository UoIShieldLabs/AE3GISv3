import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type * as api from '@/api/client';

vi.mock('../actions', () => ({ decide: vi.fn() }));

import { decide } from '../actions';
import { useAgentStore } from '../agentStore';
import { ChatView } from '../ChatView';

const chat: api.AgentChat = {
  id: 'c1',
  title: 'Build a lab',
  mode: 'full',
  topology_id: null,
  topology_name: null,
  auto_approve: false,
  owner: null,
  created_at: '2026-11-24T10:00:00Z',
  updated_at: '2026-11-24T10:00:00Z',
  active_job_id: 'job-1',
};

function msg(seq: number, role: api.AgentMessage['role'], content: Record<string, unknown>): api.AgentMessage {
  return { id: seq, seq, role, content, job_id: 'job-1', created_at: '2026-11-24T10:00:00Z' };
}

function load(canSend: boolean) {
  useAgentStore.getState().setDetail({
    ...chat,
    can_send: canSend,
    pending_approvals: [{ call_id: 'call-2', name: 'destroy', input: { topology_id: 't' } }],
    messages: [
      msg(1, 'user', { text: 'Run ping and then destroy it' }),
      msg(2, 'assistant', {
        text: 'Checking **reachability**.',
        tool_calls: [
          { id: 'call-1', name: 'run_in_node', input: { node: 'h1', command: 'ping -c1 10.0.0.1' } },
          { id: 'call-2', name: 'destroy', input: { topology_id: 't' } },
        ],
      }),
      msg(3, 'tool', { results: [{ tool_call_id: 'call-1', name: 'run_in_node', text: 'h1$ ping\n[exit 0]', is_error: false }] }),
      msg(4, 'note', { kind: 'limit', text: 'This run reached its limit.' }),
    ],
  });
}

beforeEach(() => {
  vi.mocked(decide).mockReset();
  useAgentStore.setState({ byId: {}, chats: null });
});

describe('ChatView', () => {
  it('renders replies, tool calls with their results, and notes', () => {
    load(true);
    render(<ChatView chatId="c1" />);
    expect(screen.getByText('Run ping and then destroy it')).toBeInTheDocument();
    expect(screen.getByText('reachability')).toBeInTheDocument();
    expect(screen.getByText('Run command')).toBeInTheDocument();
    expect(screen.getByText('h1$ ping -c1 10.0.0.1')).toBeInTheDocument();
    expect(screen.getByText('This run reached its limit.')).toBeInTheDocument();
    const card = screen.getByText('Run command').closest('[data-status]');
    expect(card).toHaveAttribute('data-status', 'done');
  });

  it('asks the owner to allow a risky call', () => {
    load(true);
    render(<ChatView chatId="c1" />);
    expect(screen.getByText('Destroy lab').closest('[data-status]')).toHaveAttribute('data-status', 'waiting');
    fireEvent.click(screen.getByRole('button', { name: 'Allow' }));
    expect(decide).toHaveBeenCalledWith('c1', 'call-2', true);
  });

  it('shows staff reading a chat that only its owner can approve', () => {
    load(false);
    render(<ChatView chatId="c1" />);
    expect(screen.queryByRole('button', { name: 'Allow' })).toBeNull();
    expect(screen.getByText(/Waiting for the owner/)).toBeInTheDocument();
  });

  it('pairs results with their own turn even when a model server repeats call ids', () => {
    useAgentStore.getState().setDetail({
      ...chat,
      active_job_id: null,
      can_send: true,
      pending_approvals: [],
      messages: [
        msg(1, 'user', { text: 'first' }),
        msg(2, 'assistant', { text: '', tool_calls: [{ id: 'call_0', name: 'edit_topology', input: { ops: [] } }] }),
        msg(3, 'tool', { results: [{ tool_call_id: 'call_0', name: 'edit_topology', text: 'no subnet with id x', is_error: true }] }),
        msg(4, 'user', { text: 'again' }),
        msg(5, 'assistant', { text: '', tool_calls: [{ id: 'call_0', name: 'edit_topology', input: { ops: [] } }] }),
        msg(6, 'tool', { results: [{ tool_call_id: 'call_0', name: 'edit_topology', text: 'Saved as v2', is_error: false }] }),
      ],
    });
    render(<ChatView chatId="c1" />);
    const cards = screen.getAllByText('Edit topology').map((el) => el.closest('[data-status]'));
    expect(cards.map((c) => c?.getAttribute('data-status'))).toEqual(['error', 'done']);
  });

  it('streams the reply being written', () => {
    load(true);
    useAgentStore.getState().patchChat('c1', () => ({
      run: { jobId: 'job-1', phase: 'thinking', text: 'Half a sent', thinking: '', pendingTool: null },
    }));
    render(<ChatView chatId="c1" />);
    expect(screen.getByText('Half a sent')).toBeInTheDocument();
  });
});
