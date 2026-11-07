import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import { BookOpen, Check, ChevronDown, ChevronUp, Copy, Ellipsis, Pencil, Plus, RotateCcw, SkipForward, Trash2 } from 'lucide-react';
import { undo, useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import type { Tutorial, TutorialCell } from '@/types/topology';
import { nodesOf } from '@/features/monitor/selection';
import { CommitInput } from '@/shell/inspector/CommitInput';
import { cn } from '@/lib/cn';
import { MOD } from '@/lib/keyboard';
import {
  Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger, EmptyState, IconButton, Kbd, toast,
} from '@/ui';
import { CommandCell, type NodeRef } from './CommandCell';
import { MarkdownCell } from './MarkdownCell';
import { runNextStep } from './actions';
import { isTutorialUnsaved, nextCell, progressOf } from './model';

/** One tutorial: notes and commands, stepped through on the deployed lab. */
export function TutorialNotebook({ tutorial, onSave }: { tutorial: Tutorial; onSave: () => void }) {
  const { editing, runs, blocked, unsaved, topology } = useAppShallow((s) => ({
    editing: !!s.editingTutorials[tutorial.id],
    runs: s.tutorialProgress[tutorial.id],
    blocked: s.deployStatus === 'deployed' && s.backendId ? null : 'Deploy the topology to run steps',
    unsaved: isTutorialUnsaved(tutorial.id, s.topology, s.savedTopology),
    topology: s.topology,
  }));
  const nodes = useMemo(() => new Map<string, NodeRef>(nodesOf(topology).map((n) => [n.id, n])), [topology]);
  const nodeOptions = useMemo(
    () => [...nodes.values()].map((n) => ({ value: n.id, label: n.ip ? `${n.name} · ${n.ip}` : n.name })),
    [nodes],
  );
  const cells = tutorial.cells ?? [];
  const next = nextCell(tutorial, runs);
  const progress = progressOf(tutorial, runs);
  const nextBlocked = blocked ?? (!next ? null : !nodes.has(next.containerId) ? 'Pick a node for the next step' : !next.command.trim() ? 'The next step has no command' : null);
  const [openNote, setOpenNote] = useState<string | null>(null);
  const [stepping, setStepping] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const st = () => useAppStore.getState();

  const cellEl = (id: string) =>
    [...(bodyRef.current?.querySelectorAll<HTMLElement>('[data-cell-id]') ?? [])].find((el) => el.dataset.cellId === id);

  // Keep the step "Next" will run in view while presenting.
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }
    if (next) cellEl(next.id)?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' });
  }, [next?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const add = (kind: TutorialCell['kind'], index: number) => {
    // A new command targets the node of the command before it (else after it):
    // consecutive steps usually share a terminal.
    const near = [...cells.slice(0, index)].reverse().concat(cells.slice(index)).find((c) => c.kind === 'command');
    const id = st().addTutorialCell(tutorial.id, kind, index, kind === 'command' && near?.kind === 'command' ? { containerId: near.containerId } : {});
    if (id && kind === 'markdown') setOpenNote(id);
    if (id && kind === 'command') requestAnimationFrame(() => cellEl(id)?.querySelector('textarea')?.focus());
  };

  const focusAfter = (cellId: string) => {
    const at = cells.findIndex((c) => c.id === cellId);
    const following = cells.slice(at + 1).find((c) => c.kind === 'command');
    if (!following) return;
    const el = cellEl(following.id);
    (editing ? el?.querySelector('textarea') : el)?.focus();
  };

  const stepNext = async () => {
    setStepping(true);
    try { await runNextStep(tutorial.id); } finally { setStepping(false); }
  };

  const remove = () => {
    const { id, title } = tutorial;
    st().closeTutorial(id);
    st().removeTutorial(id);
    toast(`Deleted “${title}”`, { duration: 10000, action: { label: 'Undo', onClick: () => { undo(); st().openTutorial(id); } } });
  };

  const tools = (cell: TutorialCell, index: number) => (
    <>
      <IconButton label="Move up" size="icon-xs" disabled={index === 0} onClick={() => st().moveTutorialCell(tutorial.id, index, index - 1)}><ChevronUp /></IconButton>
      <IconButton label="Move down" size="icon-xs" disabled={index === cells.length - 1} onClick={() => st().moveTutorialCell(tutorial.id, index, index + 1)}><ChevronDown /></IconButton>
      <IconButton label={cell.kind === 'command' ? 'Delete step' : 'Delete note'} size="icon-xs" onClick={() => st().removeTutorialCell(tutorial.id, cell.id)}><Trash2 /></IconButton>
    </>
  );

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
      <header className="shrink-0 space-y-2 border-b border-border px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          {editing ? (
            <div className="min-w-0 flex-1">
              <CommitInput
                className="h-7 text-sm font-semibold"
                value={tutorial.title}
                onCommit={(title) => st().updateTutorial(tutorial.id, { title })}
                validate={(v) => (v ? null : 'Give the tutorial a title')}
                aria-label="Tutorial title"
              />
            </div>
          ) : (
            <h2 className="min-w-0 flex-1 truncate text-sm font-semibold text-fg" title={tutorial.title}>{tutorial.title}</h2>
          )}
          <Button size="xs" variant={editing ? 'primary' : 'ghost'} onClick={() => { setOpenNote(null); st().setTutorialEditing(tutorial.id, !editing); }}>
            {editing ? <><Check /> Done</> : <><Pencil /> Edit</>}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <IconButton label="More" size="icon-xs"><Ellipsis /></IconButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => { const id = st().duplicateTutorial(tutorial.id); if (id) st().openTutorial(id); }}><Copy /> Duplicate</DropdownMenuItem>
              <DropdownMenuItem onSelect={() => st().resetTutorialProgress(tutorial.id)} disabled={!progress.run}><RotateCcw /> Reset progress</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="danger" onSelect={remove}><Trash2 /> Delete tutorial</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {progress.total > 0 ? (
          <div className="flex items-center gap-2.5">
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <div className="h-1 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuemin={0} aria-valuemax={progress.total} aria-valuenow={progress.run} aria-label="Steps run">
                <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${(progress.run / progress.total) * 100}%` }} />
              </div>
              <span className="text-2xs tabular-nums text-fg-muted">
                {progress.run === progress.total ? `All ${progress.total} steps run` : `${progress.run} of ${progress.total} steps run`}
              </span>
            </div>
            {next ? (
              <Button size="xs" variant="primary" disabled={!!nextBlocked || stepping} loading={stepping} title={nextBlocked ?? 'Run the next step'} onClick={() => void stepNext()}>
                {stepping ? null : <SkipForward />} Next step
              </Button>
            ) : (
              <Button size="xs" variant="secondary" onClick={() => st().resetTutorialProgress(tutorial.id)}><RotateCcw /> Start over</Button>
            )}
          </div>
        ) : null}

        {blocked && progress.total > 0 ? <p className="text-2xs text-fg-subtle">{blocked}.</p> : null}
        {unsaved ? (
          <div className="flex items-center gap-1.5 text-2xs text-fg-muted">
            <span className="size-1.5 rounded-full bg-warning" aria-hidden />
            Unsaved changes
            <Button size="xs" variant="link" className="h-auto px-1" onClick={onSave}>Save</Button>
            <Kbd>{MOD}S</Kbd>
          </div>
        ) : null}
      </header>

      <div ref={bodyRef} className="min-h-0 flex-1 overflow-y-auto px-3 pb-6 pt-3">
        {cells.length === 0 && !editing ? (
          <EmptyState
            icon={<BookOpen />}
            title="Nothing here yet"
            description="Add notes and commands. Each command runs in its node's terminal, one step at a time."
            action={<Button size="sm" onClick={() => st().setTutorialEditing(tutorial.id, true)}><Pencil /> Edit tutorial</Button>}
          />
        ) : (
          <div className={cn('flex flex-col', !editing && 'gap-3')}>
            {cells.map((cell, i) => (
              <Fragment key={cell.id}>
                {editing ? <Inserter onAdd={(kind) => add(kind, i)} /> : null}
                {cell.kind === 'markdown' ? (
                  <MarkdownCell
                    tutorialId={tutorial.id}
                    cell={cell}
                    editing={editing}
                    open={openNote === cell.id}
                    onOpen={() => setOpenNote(cell.id)}
                    onClose={() => setOpenNote((cur) => (cur === cell.id ? null : cur))}
                    tools={editing ? tools(cell, i) : undefined}
                  />
                ) : (
                  <CommandCell
                    tutorialId={tutorial.id}
                    cell={cell}
                    node={nodes.get(cell.containerId)}
                    nodeOptions={nodeOptions}
                    editing={editing}
                    isNext={next?.id === cell.id}
                    ranAt={runs?.[cell.id]}
                    blocked={blocked}
                    tools={editing ? <span className="flex opacity-0 transition-opacity group-hover/cell:opacity-100 group-focus-within/cell:opacity-100">{tools(cell, i)}</span> : undefined}
                    onRan={() => focusAfter(cell.id)}
                  />
                )}
              </Fragment>
            ))}
            {editing ? <Inserter always onAdd={(kind) => add(kind, cells.length)} /> : null}
          </div>
        )}
      </div>
    </div>
  );
}

/** "+ Note / + Command" between cells (on hover) and at the end (always). */
function Inserter({ onAdd, always }: { onAdd: (kind: TutorialCell['kind']) => void; always?: boolean }) {
  return (
    <div className={cn('flex items-center gap-1.5', always ? 'pt-3' : 'h-6 opacity-0 transition-opacity hover:opacity-100 focus-within:opacity-100')}>
      <div className="h-px flex-1 bg-border" />
      <Button size="xs" variant={always ? 'outline' : 'ghost'} onClick={() => onAdd('markdown')}><Plus /> Note</Button>
      <Button size="xs" variant={always ? 'outline' : 'ghost'} onClick={() => onAdd('command')}><Plus /> Command</Button>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}
