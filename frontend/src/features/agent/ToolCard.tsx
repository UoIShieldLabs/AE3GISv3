import { useState } from 'react';
import { Check, ChevronRight, CircleAlert, Hand, Wrench } from 'lucide-react';
import { Button, Spinner } from '@/ui';
import { cn } from '@/lib/cn';
import type { LiveApproval, LiveTool } from './agentStore';
import { decide } from './actions';
import { describeCall, toolLabel } from './toolText';

export interface ToolCardProps {
  chatId: string;
  call: { id: string; name: string; input: unknown };
  live?: LiveTool;
  result?: { text: string; is_error: boolean };
  approval?: LiveApproval;
  canSend: boolean;
}

export function ToolCard({ chatId, call, live, result, approval, canSend }: ToolCardProps) {
  const [open, setOpen] = useState(false);
  const waiting = approval?.status === 'pending';
  const status: 'waiting' | 'running' | 'error' | 'done' | 'queued' = waiting
    ? 'waiting'
    : result
      ? result.is_error ? 'error' : 'done'
      : live
        ? live.status === 'running' ? 'running' : live.status
        : 'queued';
  const summary = describeCall(call.name, call.input);
  const output = live?.output ?? '';
  const text = result?.text ?? live?.text ?? '';

  return (
    <div
      className={cn(
        'ae-agent-tool rounded-md border bg-surface-2 text-xs',
        waiting ? 'border-warning/60' : status === 'error' ? 'border-danger/40' : 'border-border',
      )}
      data-status={status}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full min-w-0 items-center gap-2 px-2 py-1.5 text-left hover:bg-hover"
        aria-expanded={open}
      >
        <ChevronRight className={cn('size-3 shrink-0 text-fg-subtle transition-transform', open && 'rotate-90')} />
        <StatusIcon status={status} />
        <span className="shrink-0 font-medium text-fg">{toolLabel(call.name)}</span>
        {summary ? <span className="min-w-0 truncate font-mono text-fg-muted">{summary}</span> : null}
      </button>
      {waiting ? (
        <div className="flex flex-wrap items-center gap-2 border-t border-border px-2 py-1.5">
          <span className="text-fg-muted">{canSend ? 'The agent wants to do this. Allow it?' : 'Waiting for the owner’s approval.'}</span>
          {canSend ? (
            <span className="ml-auto flex gap-1.5">
              <Button size="xs" variant="secondary" onClick={() => void decide(chatId, call.id, false)}>Decline</Button>
              <Button size="xs" variant="primary" onClick={() => void decide(chatId, call.id, true)}>Allow</Button>
            </span>
          ) : null}
        </div>
      ) : null}
      {open ? (
        <div className="space-y-1.5 border-t border-border px-2 py-1.5">
          <Block label="Input" text={JSON.stringify(call.input ?? {}, null, 2)} />
          {output ? <Block label="Output" text={output} /> : null}
          {text ? <Block label={status === 'error' ? 'Error' : 'Result'} text={text} danger={status === 'error'} /> : null}
        </div>
      ) : output && status === 'running' ? (
        <pre className="max-h-28 overflow-auto border-t border-border px-2 py-1 font-mono text-2xs leading-snug text-fg-muted">{output.slice(-1500)}</pre>
      ) : null}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'running') return <Spinner className="size-3 shrink-0 text-accent" />;
  if (status === 'waiting') return <Hand className="size-3 shrink-0 text-warning" />;
  if (status === 'error') return <CircleAlert className="size-3 shrink-0 text-danger" />;
  if (status === 'done') return <Check className="size-3 shrink-0 text-success" />;
  return <Wrench className="size-3 shrink-0 text-fg-subtle" />;
}

function Block({ label, text, danger }: { label: string; text: string; danger?: boolean }) {
  return (
    <div>
      <div className="mb-0.5 text-2xs font-medium uppercase tracking-wide text-fg-subtle">{label}</div>
      <pre className={cn('max-h-64 overflow-auto whitespace-pre-wrap break-words rounded border border-border bg-surface px-2 py-1 font-mono text-2xs leading-snug', danger ? 'text-danger' : 'text-fg')}>
        {text}
      </pre>
    </div>
  );
}
