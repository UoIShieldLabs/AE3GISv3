import { useEffect, useMemo, useRef } from 'react';
import { CircleAlert, CircleSlash, Hourglass, OctagonX } from 'lucide-react';
import { Markdown } from '@/features/tutorials/Markdown';
import { Spinner } from '@/ui';
import { cn } from '@/lib/cn';
import type * as api from '@/api/client';
import { resultsByTurn, useAgentStore, type ChatState } from './agentStore';
import { ToolCard } from './ToolCard';
import { toolLabel } from './toolText';

type Call = { id: string; name: string; input: unknown };

/** A chat's messages, then what the run is doing right now. Scrolls with new
 *  content unless the reader scrolled up. */
export function ChatView({ chatId }: { chatId: string }) {
  const state = useAgentStore((s) => s.byId[chatId]);
  const scroller = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  const results = useMemo(() => resultsByTurn(state?.messages ?? []), [state?.messages]);

  const tail = `${state?.messages.length ?? 0}:${state?.run?.text.length ?? 0}:${Object.keys(state?.tools ?? {}).length}:${state?.sending ?? ''}`;
  useEffect(() => {
    const el = scroller.current;
    if (el && pinned.current) el.scrollTop = el.scrollHeight;
  }, [tail]);

  if (!state) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div
      ref={scroller}
      className="min-h-0 flex-1 overflow-y-auto px-3 py-3"
      onScroll={(e) => {
        const el = e.currentTarget;
        pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
      }}
    >
      <div className="flex flex-col gap-3">
        {state.messages.map((m) => (
          <MessageRow key={m.seq} message={m} state={state} results={results} chatId={chatId} />
        ))}
        {state.sending ? <UserBubble text={state.sending} pending /> : null}
        <LiveTail state={state} />
        {state.error ? (
          <div className="flex items-start gap-2 rounded-md bg-danger-soft px-2.5 py-2 text-xs text-danger">
            <CircleAlert className="mt-px size-3.5 shrink-0" /> {state.error}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function MessageRow({
  message,
  state,
  results,
  chatId,
}: {
  message: api.AgentMessage;
  state: ChatState;
  results: Map<number, Map<string, { text: string; is_error: boolean }>>;
  chatId: string;
}) {
  const c = message.content as Record<string, unknown>;
  if (message.role === 'user') {
    const ctx = (c.context ?? null) as { topology_name?: string } | null;
    return <UserBubble text={String(c.text ?? '')} topology={ctx?.topology_name} />;
  }
  if (message.role === 'assistant') {
    const calls = (Array.isArray(c.tool_calls) ? c.tool_calls : []) as Call[];
    const text = String(c.text ?? '');
    if (!text && !calls.length) return null;
    return (
      <div className="flex flex-col gap-1.5">
        {text ? <Markdown source={text} className="ae-agent-reply" /> : null}
        {calls.map((call) => {
          const result = results.get(message.seq)?.get(call.id);
          return (
            <ToolCard
              key={call.id}
              chatId={chatId}
              call={call}
              // Live state is the run's in progress; once saved, the result speaks.
              live={result ? undefined : state.tools[call.id]}
              result={result}
              approval={result ? undefined : state.approvals[call.id]}
              canSend={state.canSend}
            />
          );
        })}
      </div>
    );
  }
  if (message.role === 'note') return <Note kind={String(c.kind ?? '')} text={String(c.text ?? '')} />;
  return null; // tool rows show inside their cards
}

function UserBubble({ text, topology, pending }: { text: string; topology?: string; pending?: boolean }) {
  return (
    <div className={cn('ml-8 flex flex-col items-end gap-0.5', pending && 'opacity-60')}>
      <div className="max-w-full whitespace-pre-wrap break-words rounded-lg rounded-br-sm bg-accent-soft px-3 py-2 text-[13px] text-fg">{text}</div>
      {topology ? <span className="text-2xs text-fg-subtle">on {topology}</span> : null}
    </div>
  );
}

function Note({ kind, text }: { kind: string; text: string }) {
  const Icon = kind === 'stopped' ? OctagonX : kind === 'limit' ? Hourglass : kind === 'refusal' ? CircleSlash : CircleAlert;
  return (
    <div className={cn('flex items-start justify-center gap-1.5 px-2 text-center text-xs', kind === 'error' ? 'text-danger' : 'text-fg-muted')}>
      <Icon className="mt-px size-3.5 shrink-0" />
      <span>{text}</span>
    </div>
  );
}

/** The run in progress: the reply being written, the model thinking, a call being prepared. */
function LiveTail({ state }: { state: ChatState }) {
  const run = state.run;
  if (!run) return null;
  if (run.text) return <Markdown source={run.text} className="ae-agent-reply" />;
  const working = Object.values(state.tools).some((t) => t.status === 'running');
  const waiting = Object.values(state.approvals).some((a) => a.status === 'pending');
  if (working || waiting) return null; // the card says what's happening
  const label = run.pendingTool ? `Preparing ${toolLabel(run.pendingTool).toLowerCase()}…` : 'Thinking…';
  return (
    <div className="flex flex-col gap-1 text-xs text-fg-muted">
      <div className="flex items-center gap-2">
        <Spinner className="size-3.5" /> {label}
      </div>
      {run.thinking ? (
        <p className="line-clamp-3 border-l-2 border-border pl-2 text-2xs italic text-fg-subtle">{run.thinking.slice(-400)}</p>
      ) : null}
    </div>
  );
}
