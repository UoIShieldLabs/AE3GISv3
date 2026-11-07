import { BookOpen, ChevronRight, Plus } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import type { Tutorial } from '@/types/topology';
import { Button, EmptyState } from '@/ui';
import { createTutorial } from './actions';
import { commandCells, progressOf } from './model';

/** The topology's tutorials, to open one or start a new one. */
export function TutorialHome({ tutorials }: { tutorials: Tutorial[] }) {
  const progress = useAppShallow((s) => s.tutorialProgress);
  if (tutorials.length === 0) {
    return (
      <EmptyState
        className="flex-1"
        icon={<BookOpen />}
        title="No tutorials yet"
        description="A tutorial mixes notes with commands that run, one step at a time, in your lab's node terminals. It's saved with this topology."
        action={<Button size="sm" variant="primary" onClick={() => createTutorial()}><Plus /> New tutorial</Button>}
      />
    );
  }
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center justify-between gap-2 px-3 pb-1 pt-3">
        <span className="ae-label text-2xs font-semibold uppercase tracking-wide text-fg-subtle">In this topology</span>
        <Button size="xs" variant="ghost" onClick={() => createTutorial()}><Plus /> New</Button>
      </div>
      <ul className="min-h-0 flex-1 overflow-y-auto px-1.5 pb-3">
        {tutorials.map((t) => {
          const { run, total } = progressOf(t, progress[t.id]);
          const notes = (t.cells ?? []).length - commandCells(t).length;
          return (
            <li key={t.id}>
              <button
                type="button"
                onClick={() => useAppStore.getState().openTutorial(t.id)}
                className="group flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-hover focus-visible:outline-2 focus-visible:outline-ring"
              >
                <BookOpen className="size-4 shrink-0 text-fg-subtle" aria-hidden />
                <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="truncate text-[13px] font-medium text-fg">{t.title}</span>
                  <span className="text-2xs text-fg-muted">
                    {total} step{total === 1 ? '' : 's'}{notes ? ` · ${notes} note${notes === 1 ? '' : 's'}` : ''}
                    {run ? <span className="text-success"> · {run}/{total} run</span> : null}
                  </span>
                </span>
                <ChevronRight className="size-3.5 shrink-0 text-fg-subtle opacity-0 transition-opacity group-hover:opacity-100" aria-hidden />
              </button>
            </li>
          );
        })}
      </ul>
      <p className="shrink-0 border-t border-border px-3 py-2 text-2xs text-fg-subtle">Tutorials are saved with this topology.</p>
    </div>
  );
}
