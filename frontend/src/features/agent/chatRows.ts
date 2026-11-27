import type * as api from '@/api/client';

export type Call = { id: string; name: string; input: unknown };
export type Result = { text: string; is_error: boolean };
/** A tool call and the assistant turn it belongs to (its result is keyed by that turn). */
export type Step = { seq: number; call: Call };

export type Row =
  | { kind: 'user'; key: string; text: string }
  | { kind: 'text'; key: string; text: string }
  | { kind: 'note'; key: string; note: string; text: string }
  | { kind: 'tool'; key: string; step: Step }
  | { kind: 'steps'; key: string; steps: Step[] };

/** A chat as rows to draw. Consecutive tool calls that finished fine fold into
 *  one `steps` row; a running, failed or approval-waiting call, any text, and a
 *  user message or note break the run. A run of one is a plain `tool` row. */
export function buildRows(messages: api.AgentMessage[], results: Map<number, Map<string, Result>>): Row[] {
  const rows: Row[] = [];
  let run: Step[] = [];
  const flush = () => {
    if (run.length === 1) rows.push({ kind: 'tool', key: `tool:${run[0].seq}:${run[0].call.id}`, step: run[0] });
    else if (run.length > 1) rows.push({ kind: 'steps', key: `steps:${run[0].seq}:${run[0].call.id}`, steps: run });
    run = [];
  };

  for (const m of messages) {
    const c = m.content as Record<string, unknown>;
    if (m.role === 'user') {
      flush();
      rows.push({ kind: 'user', key: `m:${m.seq}`, text: String(c.text ?? '') });
    } else if (m.role === 'assistant') {
      const text = String(c.text ?? '');
      if (text) {
        flush();
        rows.push({ kind: 'text', key: `m:${m.seq}`, text });
      }
      const calls = (Array.isArray(c.tool_calls) ? c.tool_calls : []) as Call[];
      for (const call of calls) {
        const result = results.get(m.seq)?.get(call.id);
        const step = { seq: m.seq, call };
        if (result && !result.is_error) {
          run.push(step);
        } else {
          flush();
          rows.push({ kind: 'tool', key: `tool:${m.seq}:${call.id}`, step });
        }
      }
    } else if (m.role === 'note') {
      flush();
      rows.push({ kind: 'note', key: `m:${m.seq}`, note: String(c.kind ?? ''), text: String(c.text ?? '') });
    }
    // `tool` rows carry results; they show inside their calls.
  }
  flush();
  return rows;
}
