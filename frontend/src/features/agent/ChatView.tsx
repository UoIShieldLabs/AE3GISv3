import { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronRight, CircleAlert, CircleSlash, Hourglass, OctagonX } from 'lucide-react';
import { Markdown } from '@/features/tutorials/Markdown';
import { Spinner } from '@/ui';
import { cn } from '@/lib/cn';
import { resultsByTurn, useAgentStore, type ChatState } from './agentStore';
import { ToolCard } from './ToolCard';
import { toolLabel } from './toolText';
import { buildRows, type Result, type Row, type Step } from './chatRows';

/** A chat's messages, then what the run is doing right now. Scrolls with new
 *  content unless the reader scrolled up. */
export function ChatView({ chatId }: { chatId: string }) {
  const state = useAgentStore((s) => s.byId[chatId]);
  const scroller = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  const results = useMemo(() => resultsByTurn(state?.messages ?? []), [state?.messages]);
  const rows = useMemo(() => buildRows(state?.messages ?? [], results), [state?.messages, results]);

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
        {rows.map((row) => (
          <RowView key={row.key} row={row} state={state} results={results} chatId={chatId} />
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

function RowView({ row, state, results, chatId }: { row: Row; state: ChatState; results: Map<number, Map<string, Result>>; chatId: string }) {
  switch (row.kind) {
    case 'user':
      return <UserBubble text={row.text} />;
    case 'text':
      return <Markdown source={row.text} className="ae-agent-reply" />;
    case 'note':
      return <Note kind={row.note} text={row.text} />;
    case 'tool':
      return <StepCard step={row.step} state={state} results={results} chatId={chatId} />;
    case 'steps':
      return <StepGroup steps={row.steps} state={state} results={results} chatId={chatId} />;
  }
}

function StepCard({ step, state, results, chatId }: { step: Step; state: ChatState; results: Map<number, Map<string, Result>>; chatId: string }) {
  const result = results.get(step.seq)?.get(step.call.id);
  return (
    <ToolCard
      chatId={chatId}
      call={step.call}
      // Live state is the run's in progress; once saved, the result speaks.
      live={result ? undefined : state.tools[step.call.id]}
      result={result}
      approval={result ? undefined : state.approvals[step.call.id]}
      canSend={state.canSend}
    />
  );
}

/** Finished steps folded into one line; open to see each. */
function StepGroup({ steps, state, results, chatId }: { steps: Step[]; state: ChatState; results: Map<number, Map<string, Result>>; chatId: string }) {
  const [open, setOpen] = useState(false);
  const names = [...new Set(steps.map((s) => toolLabel(s.call.name)))];
  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex min-w-0 items-center gap-2 rounded-md px-2 py-1 text-left text-xs text-fg-muted hover:bg-hover"
      >
        <ChevronRight className={cn('size-3 shrink-0 text-fg-subtle transition-transform', open && 'rotate-90')} />
        <Check className="size-3.5 shrink-0 text-success" />
        <span className="shrink-0 font-medium text-fg">{steps.length} steps</span>
        <span className="min-w-0 truncate text-fg-subtle">{names.join(', ')}</span>
      </button>
      {open ? (
        <div className="flex flex-col gap-1.5 border-l-2 border-border pl-2">
          {steps.map((s) => (
            <StepCard key={s.call.id} step={s} state={state} results={results} chatId={chatId} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function UserBubble({ text, pending }: { text: string; pending?: boolean }) {
  return (
    <div className={cn('ml-8 flex flex-col items-end', pending && 'opacity-60')}>
      <div className="max-w-full whitespace-pre-wrap break-words rounded-lg rounded-br-sm bg-accent-soft px-3 py-2 text-[13px] text-fg">{text}</div>
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
        <p className="truncate pl-5 text-2xs italic text-fg-subtle">{run.thinking.slice(-200)}</p>
      ) : null}
    </div>
  );
}
