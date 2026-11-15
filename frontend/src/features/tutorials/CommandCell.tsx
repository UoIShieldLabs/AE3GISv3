import { useState } from 'react';
import { Check, Play, Square, TriangleAlert, X } from 'lucide-react';
import { useAppStore, type CellStatus } from '@/store';
import type { TutorialCommandCell } from '@/types/topology';
import { cn } from '@/lib/cn';
import { Badge, IconButton, Select, Spinner, type SelectOption } from '@/ui';
import { CommitTextarea } from './CommitTextarea';
import { runTutorialCell, stopTutorialCell } from './actions';

export interface NodeRef { id: string; name: string; type: string; ip?: string }

export interface CommandCellProps {
  tutorialId: string;
  cell: TutorialCommandCell;
  node: NodeRef | undefined;
  nodeOptions: SelectOption[];
  editing: boolean;
  isNext: boolean;
  ranAt: number | undefined;
  /** How the last run is doing (from the shell's prompt markers). */
  status?: CellStatus;
  /** The node's colour in this tutorial (also its ring on the canvas). */
  color?: string;
  /** Why it can't run right now (not deployed), shown on the Run button. */
  blocked: string | null;
  /** Edit-mode cell tools (move, delete), rendered in the header. */
  tools?: React.ReactNode;
  /** Shift+Enter: after running, hand focus to the next step. */
  onRan?: () => void;
}

const timeOf = (at: number) => new Date(at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

/** A command typed into a node's terminal: node, command, Run and whether it ran. */
export function CommandCell({ tutorialId, cell, node, nodeOptions, editing, isNext, ranAt, status, color, blocked, tools, onRan }: CommandCellProps) {
  const [pending, setPending] = useState(false);
  const running = status?.state === 'running';
  const missing = !!cell.containerId && !node;
  const empty = !cell.command.trim();
  const reason = blocked ?? (!node ? 'Pick a node for this step' : empty ? 'Write a command first' : null);

  const run = async () => {
    if (reason || pending || running) return;
    setPending(true);
    try {
      if (await runTutorialCell(tutorialId, cell.id)) onRan?.();
    } finally {
      setPending(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== 'Enter' || !e.shiftKey) return;
    e.preventDefault();
    e.stopPropagation();
    // A textarea commits on blur; let it, then run what was written.
    (e.target as HTMLElement).blur?.();
    requestAnimationFrame(() => void run());
  };

  return (
    <div
      data-cell-id={cell.id}
      tabIndex={editing ? undefined : 0}
      onKeyDown={editing ? undefined : onKeyDown}
      data-cell-state={ranAt !== undefined ? status?.state ?? 'sent' : undefined}
      className={cn(
        'group/cell rounded-md border bg-surface-2/40 outline-none transition-colors',
        'focus-visible:ring-2 focus-visible:ring-accent/40',
        isNext ? 'border-accent/70' : 'border-border',
      )}
      // The bar wears the node's colour: the same one rings the node on the canvas.
      style={color && node ? { boxShadow: `inset 3px 0 0 ${color}` } : undefined}
    >
      <div className="flex min-h-8 items-center gap-1.5 border-b border-border/70 py-1 pl-2.5 pr-1">
        {editing ? (
          <Select
            size="sm"
            className="h-6 w-auto min-w-28 max-w-[60%] text-xs"
            value={cell.containerId || undefined}
            onValueChange={(containerId) => useAppStore.getState().updateTutorialCell(tutorialId, cell.id, { containerId })}
            options={nodeOptions}
            placeholder="Pick a node"
            aria-label="Node"
          />
        ) : (
          <NodeChip node={node} missing={missing} color={color} />
        )}
        <div className="ml-auto flex shrink-0 items-center gap-1">
          {missing && editing ? <Badge tone="warning">node removed</Badge> : null}
          {ranAt !== undefined ? <RunStatus ranAt={ranAt} status={status} /> : isNext ? <Badge tone="accent">next</Badge> : null}
          {tools}
          {running ? (
            <IconButton
              label={`Stop on ${node?.name ?? 'node'}`}
              tooltip="Stop (Ctrl-C in its terminal)"
              size="icon-xs"
              variant="ghost"
              onClick={() => void stopTutorialCell(tutorialId, cell.id)}
            >
              <Square />
            </IconButton>
          ) : (
            <IconButton
              label={`Run on ${node?.name ?? 'node'}`}
              tooltip={reason ?? (editing ? 'Run this step' : 'Run this step (Shift+Enter)')}
              size="icon-xs"
              variant={isNext && !reason ? 'primary' : 'ghost'}
              disabled={!!reason || pending}
              onClick={() => void run()}
            >
              {pending ? <Spinner className="size-3" /> : <Play />}
            </IconButton>
          )}
        </div>
      </div>
      {editing ? (
        <div className="p-1.5">
          <CommitTextarea
            className="border-transparent bg-transparent px-1.5 py-1 font-mono text-xs hover:border-border focus:bg-surface"
            value={cell.command}
            onCommit={(command) => useAppStore.getState().updateTutorialCell(tutorialId, cell.id, { command })}
            onKeyDown={onKeyDown}
            placeholder="command, e.g. ssh root@10.0.5.20"
            aria-label="Command"
            spellCheck={false}
          />
        </div>
      ) : (
        <pre className={cn('overflow-x-auto whitespace-pre-wrap break-words px-3 py-2 font-mono text-xs leading-relaxed', empty ? 'italic text-fg-subtle' : 'text-fg')}>
          {empty ? 'No command yet' : cell.command}
        </pre>
      )}
    </div>
  );
}

/** Where the last run stands: still running, how it ended, or just "sent" when
 *  the shell can't tell (it went into an ssh, or the image prints no markers). */
function RunStatus({ ranAt, status }: { ranAt: number; status: CellStatus | undefined }) {
  const at = timeOf(ranAt);
  const title = `Ran at ${new Date(ranAt).toLocaleTimeString()}`;
  if (status?.state === 'running') {
    return (
      <span className="flex items-center gap-1 text-2xs text-fg-muted" title={title}>
        <Spinner className="size-3" /> running
      </span>
    );
  }
  if (status?.state === 'done' && status.stopped) {
    return <span className="text-2xs text-fg-muted" title={`${title}; stopped`}>stopped</span>;
  }
  if (status?.state === 'done' && status.exit) {
    return (
      <span className="flex items-center gap-1 text-2xs text-danger" title={`${title}; ended with exit code ${status.exit}`}>
        <X className="size-3" aria-hidden /> exit {status.exit}
      </span>
    );
  }
  if (status?.state === 'done') {
    return (
      <span className="flex items-center gap-1 text-2xs text-success" title={title}>
        <Check className="size-3" aria-hidden /> {at}
      </span>
    );
  }
  return <span className="text-2xs text-fg-muted" title={`${title}. The shell doesn't report when this one ends.`}>sent {at}</span>;
}

function NodeChip({ node, missing, color }: { node: NodeRef | undefined; missing: boolean; color?: string }) {
  if (missing) {
    return (
      <span className="flex min-w-0 items-center gap-1 text-xs text-warning">
        <TriangleAlert className="size-3.5 shrink-0" aria-hidden /> Node removed — edit to pick another
      </span>
    );
  }
  if (!node) return <span className="text-xs text-fg-subtle">No node picked</span>;
  return (
    <span className="flex min-w-0 items-center gap-1.5 text-xs">
      <span className="size-2 shrink-0 rounded-full bg-fg-subtle" style={color ? { backgroundColor: color } : undefined} aria-hidden />
      <span className="truncate font-medium text-fg">{node.name}</span>
      {node.ip ? <span className="truncate font-mono text-2xs text-fg-subtle">{node.ip}</span> : null}
    </span>
  );
}
