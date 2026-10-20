import { useEffect, useRef, useState } from 'react';
import * as api from '@/api/client';

export interface StepView {
  index: number;
  container_id: string;
  command: string;
  status: string; // running | ok | failed | timeout | error | stopped
  exit_code: number | null;
  stdout: string;
  stderr: string;
}

export interface ScenarioStream {
  run: api.ScenarioRun | null;
  steps: StepView[];
  ended: boolean;
  connection: 'connecting' | 'open' | 'closed';
}

type Message =
  | { type: 'hello'; run: api.ScenarioRun | null; backlog: { steps: api.ScenarioStepResult[] } }
  | { type: 'step'; index: number; status: string; container_id?: string; command?: string; exit_code?: number | null }
  | { type: 'output'; index: number; stream: 'stdout' | 'stderr'; text: string }
  | { type: 'end'; result: Record<string, unknown> | null };

const TICK_MS = 250;

function seed(result: api.ScenarioStepResult): StepView {
  return {
    index: result.index,
    container_id: result.container_id,
    command: result.command,
    status: result.status,
    exit_code: result.exit_code ?? null,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
  };
}

/** A scenario run's per-step output, live over its WebSocket (completed steps
 *  first, then streamed output), re-rendered a few times a second. */
export function useScenarioStream(topologyId: string | null, jobId: string): ScenarioStream {
  const [state, setState] = useState<ScenarioStream>({ run: null, steps: [], ended: false, connection: 'connecting' });
  const buf = useRef({ steps: new Map<number, StepView>(), dirty: false });

  useEffect(() => {
    if (!topologyId) return;
    let closed = false;
    let ended = false;
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    const b = buf.current;
    b.steps = new Map();

    const at = (index: number): StepView => {
      let s = b.steps.get(index);
      if (!s) { s = { index, container_id: '', command: '', status: 'running', exit_code: null, stdout: '', stderr: '' }; b.steps.set(index, s); }
      return s;
    };
    const flush = () => {
      if (!b.dirty) return;
      b.dirty = false;
      setState((s) => ({ ...s, steps: [...b.steps.values()].sort((x, y) => x.index - y.index) }));
    };
    const tick = setInterval(flush, TICK_MS);

    const connect = () => {
      setState((s) => ({ ...s, connection: 'connecting' }));
      ws = new WebSocket(api.wsUrl(api.scenarioWsPath(topologyId, jobId)));
      ws.onopen = () => setState((s) => ({ ...s, connection: 'open' }));
      ws.onmessage = (ev: MessageEvent<string>) => {
        let msg: Message;
        try { msg = JSON.parse(ev.data) as Message; } catch { return; }
        switch (msg.type) {
          case 'hello':
            for (const r of msg.backlog.steps ?? []) b.steps.set(r.index, seed(r));
            b.dirty = true;
            setState((s) => ({ ...s, run: msg.run }));
            flush();
            break;
          case 'step': {
            const s = at(msg.index);
            s.status = msg.status;
            if (msg.container_id) s.container_id = msg.container_id;
            if (msg.command) s.command = msg.command;
            if (msg.exit_code !== undefined) s.exit_code = msg.exit_code ?? null;
            b.dirty = true;
            break;
          }
          case 'output': {
            const s = at(msg.index);
            if (msg.stream === 'stderr') s.stderr += msg.text;
            else s.stdout += msg.text;
            b.dirty = true;
            break;
          }
          case 'end':
            ended = true;
            flush();
            void api.getScenarioRun(jobId).then(
              (run) => setState((s) => ({ ...s, run, ended: true })),
              () => setState((s) => ({ ...s, ended: true })),
            );
            break;
        }
      };
      ws.onclose = () => {
        setState((s) => ({ ...s, connection: 'closed' }));
        if (!closed && !ended) retry = setTimeout(connect, 2000);
      };
    };
    connect();
    return () => {
      closed = true;
      clearInterval(tick);
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, [topologyId, jobId]);

  return state;
}
