import { describe, expect, it } from 'vitest';
import type * as api from '@/api/client';
import { resultsByTurn } from '../agentStore';
import { buildRows } from '../chatRows';

const msg = (seq: number, role: api.AgentMessage['role'], content: Record<string, unknown>): api.AgentMessage => ({
  id: seq,
  seq,
  role,
  content,
  job_id: 'job-1',
  created_at: '2026-11-27T10:00:00Z',
});
const call = (id: string, name = 'get_topology') => ({ id, name, input: {} });
const ok = (id: string) => ({ tool_call_id: id, name: 'x', text: 'fine', is_error: false });
const failed = (id: string) => ({ tool_call_id: id, name: 'x', text: 'nope', is_error: true });

function rows(messages: api.AgentMessage[]) {
  return buildRows(messages, resultsByTurn(messages)).map((r) =>
    r.kind === 'steps' ? `steps:${r.steps.map((s) => s.call.id).join(',')}` : r.kind === 'tool' ? `tool:${r.step.call.id}` : r.kind,
  );
}

describe('buildRows', () => {
  it('folds finished steps across turns into one row', () => {
    expect(
      rows([
        msg(1, 'user', { text: 'go' }),
        msg(2, 'assistant', { text: '', tool_calls: [call('a'), call('b')] }),
        msg(3, 'tool', { results: [ok('a'), ok('b')] }),
        msg(4, 'assistant', { text: '', tool_calls: [call('c')] }),
        msg(5, 'tool', { results: [ok('c')] }),
        msg(6, 'assistant', { text: 'Done.' }),
      ]),
    ).toEqual(['user', 'steps:a,b,c', 'text']);
  });

  it('keeps a failed step, and one still running or waiting, on its own', () => {
    expect(
      rows([
        msg(1, 'assistant', { text: '', tool_calls: [call('a'), call('b'), call('c'), call('d'), call('e')] }),
        msg(2, 'tool', { results: [ok('a'), ok('b'), failed('c'), ok('d')] }),
      ]),
    ).toEqual(['steps:a,b', 'tool:c', 'tool:d', 'tool:e']);
  });

  it('breaks a run at text and notes; one step is a plain card', () => {
    expect(
      rows([
        msg(1, 'assistant', { text: '', tool_calls: [call('a')] }),
        msg(2, 'tool', { results: [ok('a')] }),
        msg(3, 'assistant', { text: 'Now deploying.', tool_calls: [call('b'), call('c')] }),
        msg(4, 'tool', { results: [ok('b'), ok('c')] }),
        msg(5, 'note', { kind: 'stopped', text: 'Stopped.' }),
      ]),
    ).toEqual(['tool:a', 'text', 'steps:b,c', 'note']);
  });
});
