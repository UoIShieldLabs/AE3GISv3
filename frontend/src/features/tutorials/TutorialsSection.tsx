import { useMemo } from 'react';
import { BookOpen, Plus, X } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import type { TopologyData, Tutorial } from '@/types/topology';
import { cn } from '@/lib/cn';
import { hasMod } from '@/lib/keyboard';
import { IconButton } from '@/ui';
import { createTutorial } from './actions';
import { isTutorialUnsaved } from './model';
import { TutorialHome } from './TutorialHome';
import { TutorialNotebook } from './TutorialNotebook';

// Stable fallback: a fresh `[]` inside the selector would change identity on
// every store read and make the shallow-equal subscription loop forever.
const NO_TUTORIALS: Tutorial[] = [];

/** The Tutorials section of the right column: a tab per open tutorial, plus the list. */
export function TutorialsSection({ onSave }: { onSave: () => void }) {
  const { stored, openIds, activeId, topology, saved } = useAppShallow((s) => ({
    stored: (s.topology as TopologyData).tutorials,
    openIds: s.openTutorialIds,
    activeId: s.activeTutorialId,
    topology: s.topology,
    saved: s.savedTopology,
  }));
  const tutorials = stored ?? NO_TUTORIALS;
  // Tabs whose tutorial is gone (deleted, undone, reloaded) simply don't show.
  const open = useMemo(
    () => openIds.map((id) => tutorials.find((t) => t.id === id)).filter((t): t is Tutorial => !!t),
    [openIds, tutorials],
  );
  const active = open.find((t) => t.id === activeId) ?? null;
  const st = () => useAppStore.getState();

  return (
    <section
      aria-label="Tutorials"
      className="flex h-full min-h-0 min-w-0 flex-col bg-surface"
      // Plain keys here are for the panel, not the canvas (Delete, Enter, E…).
      onKeyDown={(e) => { if (!hasMod(e) && !e.altKey) e.stopPropagation(); }}
    >
      <div className="ae-panel-header flex h-9 shrink-0 items-stretch border-b border-border">
        <div role="tablist" aria-label="Open tutorials" className="flex min-w-0 flex-1 items-stretch overflow-x-auto">
          <Tab active={!active} onSelect={() => st().setActiveTutorial(null)} label="All tutorials">
            <BookOpen className="size-3.5 shrink-0" aria-hidden />
            {open.length === 0 ? <span className="ae-panel-title font-semibold">Tutorials</span> : null}
          </Tab>
          {open.map((t) => (
            <Tab key={t.id} active={active?.id === t.id} onSelect={() => st().setActiveTutorial(t.id)} onClose={() => st().closeTutorial(t.id)} label={t.title}>
              <span className="max-w-36 truncate font-medium">{t.title}</span>
              {isTutorialUnsaved(t.id, topology, saved) ? <span className="size-1.5 shrink-0 rounded-full bg-warning" aria-label="unsaved changes" /> : null}
            </Tab>
          ))}
        </div>
        <div className="flex shrink-0 items-center gap-0.5 px-1">
          <IconButton label="New tutorial" size="icon-xs" onClick={() => createTutorial()}><Plus /></IconButton>
          <IconButton label="Close tutorials" size="icon-xs" onClick={() => st().setTutorialsOpen(false)}><X /></IconButton>
        </div>
      </div>
      {active ? <TutorialNotebook key={active.id} tutorial={active} onSave={onSave} /> : <TutorialHome tutorials={tutorials} />}
    </section>
  );
}

function Tab({ active, onSelect, onClose, label, children }: {
  active: boolean;
  onSelect: () => void;
  onClose?: () => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div
      role="tab"
      tabIndex={0}
      aria-selected={active}
      aria-label={label}
      title={label}
      onClick={onSelect}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(); } }}
      className={cn(
        'group flex shrink-0 cursor-default items-center gap-1.5 border-r border-border px-2.5 text-xs outline-none focus-visible:bg-hover',
        active ? 'bg-surface text-fg shadow-[inset_0_-2px_0_var(--accent)]' : 'text-fg-muted hover:bg-hover hover:text-fg',
      )}
    >
      {children}
      {onClose ? (
        <IconButton label={`Close ${label}`} size="icon-xs" tooltip={false} className="-mr-1 opacity-50 group-hover:opacity-100"
          onClick={(e) => { e.stopPropagation(); onClose(); }}>
          <X />
        </IconButton>
      ) : null}
    </div>
  );
}
