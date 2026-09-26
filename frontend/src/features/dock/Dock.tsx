import { Suspense, lazy } from 'react';
import { Activity as ActivityIcon, ChevronDown, ChevronUp, Radio, SquareTerminal, X } from 'lucide-react';
import { useAppStore, type DockTab } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { cn } from '@/lib/cn';
import { IconButton, Spinner } from '@/ui';

// Heavy bodies load on first use: xterm (~400 kB), the capture table, charts.
const TerminalSession = lazy(() => import('@/features/terminal/TerminalSession').then((m) => ({ default: m.TerminalSession })));
const CaptureView = lazy(() => import('@/features/capture/CaptureView').then((m) => ({ default: m.CaptureView })));
const TrafficPanel = lazy(() => import('@/features/traffic/TrafficPanel').then((m) => ({ default: m.TrafficPanel })));

const ICONS = { terminal: SquareTerminal, capture: Radio, traffic: ActivityIcon } as const;

function title(tab: DockTab): string {
  return tab.kind === 'terminal' ? tab.name : tab.title;
}

/** Every tab stays mounted (hidden when inactive) so terminals keep their
 *  session and live views keep streaming while another tab is shown. */
function Body({ tab, active }: { tab: DockTab; active: boolean }) {
  switch (tab.kind) {
    case 'terminal':
      return <TerminalSession containerId={tab.containerId} active={active} />;
    case 'capture':
      return <div className={active ? 'flex h-full min-h-0 flex-1' : 'hidden'}><CaptureView jobId={tab.jobId} /></div>;
    case 'traffic':
      return <div className={active ? 'flex h-full min-h-0 flex-1' : 'hidden'}><TrafficPanel tabId={tab.id} jobId={tab.jobId} /></div>;
  }
}

/** Bottom dock: a tab strip over terminals, live captures and traffic runs. */
export function Dock() {
  const { tabs, activeId, minimized, live } = useAppShallow((s) => ({
    tabs: s.dockTabs,
    activeId: s.activeDockTabId,
    minimized: s.dockMinimized,
    live: s.activity.map((a) => a.job_id).join(' '),
  }));
  const { closeDockTab, setActiveDockTab, setDockMinimized } = useAppStore.getState();
  if (tabs.length === 0) return null;

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <div className="flex h-8 shrink-0 items-stretch border-y border-border bg-surface-2/60">
        <div role="tablist" className="flex min-w-0 flex-1 items-stretch overflow-x-auto">
          {tabs.map((t) => {
            const active = t.id === activeId && !minimized;
            const Icon = ICONS[t.kind];
            const running = t.kind !== 'terminal' && !!t.jobId && live.includes(t.jobId);
            return (
              <div
                key={t.id}
                role="tab"
                aria-selected={active}
                onClick={() => (t.id === activeId && !minimized ? setDockMinimized(true) : setActiveDockTab(t.id))}
                className={cn(
                  'group flex cursor-default items-center gap-2 border-r border-border px-3 text-xs',
                  active ? 'bg-surface text-fg shadow-[inset_0_2px_0_var(--accent)]' : 'text-fg-muted hover:bg-hover hover:text-fg',
                )}
              >
                <Icon className="size-3.5 shrink-0 opacity-70" aria-hidden />
                <span className="max-w-56 truncate font-medium">{title(t)}</span>
                {t.kind === 'terminal' && t.ip ? <span className="font-mono text-2xs text-fg-subtle">{t.ip}</span> : null}
                {running ? <span className="size-1.5 shrink-0 animate-pulse rounded-full bg-success" aria-label="running" /> : null}
                <IconButton label="Close" size="icon-xs" tooltip={false} className="-mr-1.5 opacity-50 group-hover:opacity-100" onClick={(e) => { e.stopPropagation(); closeDockTab(t.id); }}><X /></IconButton>
              </div>
            );
          })}
        </div>
        <IconButton label={minimized ? 'Restore dock' : 'Minimize dock'} size="icon-sm" className="m-0.5" onClick={() => setDockMinimized(!minimized)}>
          {minimized ? <ChevronUp /> : <ChevronDown />}
        </IconButton>
      </div>
      {!minimized ? (
        <div className="min-h-0 flex-1 bg-canvas">
          <Suspense fallback={<div className="flex h-full items-center justify-center"><Spinner /></div>}>
            {tabs.map((t) => <Body key={t.id} tab={t} active={t.id === activeId} />)}
          </Suspense>
        </div>
      ) : null}
    </div>
  );
}
