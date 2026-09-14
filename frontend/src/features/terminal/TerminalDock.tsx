import { Suspense, lazy } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { cn } from '@/lib/cn';
import { IconButton, Spinner } from '@/ui';

// xterm is ~400 kB; only load it once a terminal is actually opened.
const TerminalSession = lazy(() => import('./TerminalSession').then((m) => ({ default: m.TerminalSession })));

/** Bottom dock: tab strip + one live xterm per open container. */
export function TerminalDock() {
  const { terminals, activeId, minimized } = useAppShallow((s) => ({ terminals: s.terminals, activeId: s.activeTerminalId, minimized: s.terminalMinimized }));
  const { closeTerminal, setActiveTerminal, setTerminalMinimized } = useAppStore.getState();
  if (terminals.length === 0) return null;

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <div className="flex h-8 shrink-0 items-stretch border-y border-border bg-surface-2/60">
        <div className="flex min-w-0 flex-1 items-stretch overflow-x-auto">
          {terminals.map((t) => {
            const active = t.id === activeId && !minimized;
            return (
              <div
                key={t.id}
                role="tab"
                aria-selected={active}
                onClick={() => (t.id === activeId && !minimized ? setTerminalMinimized(true) : setActiveTerminal(t.id))}
                className={cn(
                  'group flex cursor-default items-center gap-2 border-r border-border px-3 text-xs',
                  active ? 'bg-surface text-fg shadow-[inset_0_2px_0_var(--accent)]' : 'text-fg-muted hover:bg-hover hover:text-fg',
                )}
              >
                <span className="truncate font-medium">{t.name}</span>
                {t.ip ? <span className="font-mono text-2xs text-fg-subtle">{t.ip}</span> : null}
                <IconButton label="Close" size="icon-xs" tooltip={false} className="-mr-1.5 opacity-50 group-hover:opacity-100" onClick={(e) => { e.stopPropagation(); closeTerminal(t.id); }}><X /></IconButton>
              </div>
            );
          })}
        </div>
        <IconButton label={minimized ? 'Restore terminals' : 'Minimize terminals'} size="icon-sm" className="m-0.5" onClick={() => setTerminalMinimized(!minimized)}>
          {minimized ? <ChevronUp /> : <ChevronDown />}
        </IconButton>
      </div>
      {!minimized ? (
        <div className="min-h-0 flex-1 bg-canvas">
          <Suspense fallback={<div className="flex h-full items-center justify-center"><Spinner /></div>}>
            {terminals.map((t) => <TerminalSession key={t.id} containerId={t.id} active={t.id === activeId} />)}
          </Suspense>
        </div>
      ) : null}
    </div>
  );
}
