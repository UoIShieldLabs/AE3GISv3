import { useEffect, useState } from 'react';
import { Check, ChevronRight, CircleDashed, TriangleAlert, X } from 'lucide-react';
import type { Tutorial } from '@/types/topology';
import { cn } from '@/lib/cn';
import { Button, Spinner, Switch } from '@/ui';
import { expandTraffic, rowSummary, rowWhat, type SetupNode } from './model';
import { useLabSetup, type RowLive } from './useLabSetup';

const timeOf = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

/** What a tutorial needs before its first step: commands that prepare the lab
 *  ("Configure lab") and traffic that keeps running in the background (one
 *  switch for all of it). One quiet row until opened. */
export function LabSetup({ tutorial, nodes, colors }: {
  tutorial: Tutorial;
  nodes: ReadonlyMap<string, SetupNode>;
  colors: ReadonlyMap<string, string>;
}) {
  const view = useLabSetup(tutorial, nodes);
  const steps = (tutorial.setup?.steps ?? []).filter((s) => s.containerId && s.command.trim());
  const traffic = tutorial.setup?.traffic ?? [];
  const { setup, traffic: live, blocked } = view;
  const [open, setOpen] = useState(false);
  const [shown, setShown] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  // A failed setup is the one thing worth opening by itself.
  useEffect(() => { if (setup.state === 'failed') setOpen(true); }, [setup.state]);

  const configure = async () => {
    setWorking(true);
    try { await view.configure(); } finally { setWorking(false); }
  };
  const busy = working || setup.state === 'running';
  const trafficBusy = live.state === 'starting' || live.state === 'stopping';
  const trafficOn = live.state === 'on' || live.state === 'starting';
  const problems = expandTraffic(tutorial.setup, nodes).problems;
  const failedAt = setup.steps.findIndex((s) => s.status !== 'ok' && s.status !== 'running');

  return (
    <section aria-label="Lab setup" className="shrink-0 border-b border-border bg-surface-2/40">
      <div className="flex min-h-9 items-center gap-2 px-3 py-1.5">
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
          className="flex min-w-0 items-center gap-1 rounded-sm text-left text-xs font-medium text-fg outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
        >
          <ChevronRight className={cn('size-3.5 shrink-0 text-fg-subtle transition-transform', open && 'rotate-90')} aria-hidden />
          <span className="shrink-0">Lab setup</span>
          <SetupStatus state={steps.length ? setup.state : null} at={setup.at} done={setup.steps.length} total={steps.length} failedAt={failedAt} trafficOn={live.state === 'on'} hasTraffic={traffic.length > 0} />
        </button>
        <div className="ml-auto flex shrink-0 items-center gap-2.5">
          {traffic.length ? (
            <label className="flex items-center gap-1.5 text-2xs text-fg-muted" title={blocked ?? (live.other ? "Another tutorial's traffic is running: switch it off to start this one's" : 'Start or stop all background traffic')}>
              Traffic
              <Switch
                aria-label="Background traffic"
                checked={trafficOn}
                disabled={!!blocked || trafficBusy}
                onCheckedChange={(on) => void view.setTraffic(on)}
              />
            </label>
          ) : null}
          {steps.length ? (
            <Button
              size="xs"
              variant={setup.state === 'done' ? 'ghost' : 'primary'}
              disabled={!!blocked || busy || setup.state === 'unknown'}
              loading={busy}
              title={blocked ?? (traffic.length ? 'Run the setup steps, then start the background traffic' : 'Run the setup steps')}
              onClick={() => void configure()}
            >
              {setup.state === 'done' ? 'Run again' : setup.state === 'failed' ? 'Try again' : 'Configure lab'}
            </Button>
          ) : null}
        </div>
      </div>

      {open ? (
        <div className="max-h-72 space-y-2.5 overflow-y-auto px-3 pb-2.5">
          {steps.length ? (
            <ol className="space-y-0.5" aria-label="Setup steps">
              {steps.map((step, i) => {
                const result = setup.steps[i];
                const running = setup.state === 'running' && i === setup.steps.length;
                const output = result ? [result.stdout, result.stderr].filter(Boolean).join('\n').trim() : '';
                const key = `step:${step.id}`;
                return (
                  <li key={step.id}>
                    <Row
                      icon={running ? <Spinner className="size-3" /> : result ? (result.status === 'ok' ? <Check className="size-3 text-success" /> : <X className="size-3 text-danger" />) : <CircleDashed className="size-3 text-fg-subtle" />}
                      color={colors.get(step.containerId)}
                      who={nodes.get(step.containerId)?.name ?? 'removed node'}
                      what={step.command}
                      note={result && result.status !== 'ok' ? (result.status === 'failed' ? `exit ${result.exit_code}` : result.status) : undefined}
                      noteTone="danger"
                      expandable={!!output}
                      expanded={shown === key}
                      onToggle={() => setShown((cur) => (cur === key ? null : key))}
                    />
                    {shown === key && output ? <Output text={output} /> : null}
                  </li>
                );
              })}
            </ol>
          ) : null}

          {traffic.length ? (
            <div>
              <div className="flex items-center gap-2 pb-0.5">
                <span className="ae-label text-2xs font-semibold uppercase tracking-wide text-fg-subtle">Background traffic</span>
                <span className="text-2xs text-fg-muted">
                  {live.other ? "another tutorial's is running" : live.state === 'on' ? 'running' : live.state === 'off' ? 'off' : `${live.state}…`}
                </span>
              </div>
              <ul className="space-y-0.5" aria-label="Background traffic">
                {traffic.map((row, i) => {
                  const state: RowLive | undefined = live.rows[i];
                  const problem = problems[row.id];
                  const output = state?.ended?.output || state?.output || '';
                  const key = `traffic:${row.id}`;
                  return (
                    <li key={row.id}>
                      <Row
                        icon={problem ? <TriangleAlert className="size-3 text-warning" /> : <span className={cn('size-1.5 rounded-full', state?.running ? 'bg-success' : state?.ended ? 'bg-danger' : 'bg-border-strong')} />}
                        who={row.label?.trim() || rowSummary(row, nodes)}
                        what={row.label?.trim() ? `${rowSummary(row, nodes)} · ${rowWhat(row)}` : rowWhat(row)}
                        note={problem ?? (state?.ended && !state.running ? `ended${state.ended.exit ? ` (exit ${state.ended.exit})` : ''}` : state?.ended ? `${state.running} of ${state.total} running` : undefined)}
                        noteTone={problem ? 'warning' : 'danger'}
                        expandable={!!output}
                        expanded={shown === key}
                        onToggle={() => setShown((cur) => (cur === key ? null : key))}
                      />
                      {shown === key && output ? <Output text={output} /> : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function SetupStatus({ state, at, done, total, failedAt, trafficOn, hasTraffic }: {
  state: ReturnType<typeof useLabSetup>['setup']['state'] | null;
  at: string | null;
  done: number;
  total: number;
  failedAt: number;
  trafficOn: boolean;
  hasTraffic: boolean;
}) {
  const base = 'min-w-0 truncate text-2xs font-normal';
  // Traffic only: the switch is the whole story.
  if (state === null) return <span className={cn(base, 'text-fg-muted')}>{hasTraffic ? (trafficOn ? 'traffic running' : 'traffic off') : ''}</span>;
  if (state === 'unknown') return null;
  if (state === 'running') return <span className={cn(base, 'text-fg-muted')}>{Math.min(done + 1, total)} of {total}…</span>;
  if (state === 'failed') return <span className={cn(base, 'text-danger')}>{failedAt >= 0 ? `step ${failedAt + 1} failed` : 'did not finish'}</span>;
  if (state === 'done') return <span className={cn(base, 'flex items-center gap-1 text-success')} title={at ? `Configured at ${timeOf(at)}` : undefined}><Check className="size-3 shrink-0" aria-hidden />configured</span>;
  return <span className={cn(base, 'text-fg-muted')}>not run yet</span>;
}

function Row({ icon, color, who, what, note, noteTone, expandable, expanded, onToggle }: {
  icon: React.ReactNode;
  color?: string;
  who: string;
  what: string;
  note?: string;
  noteTone?: 'danger' | 'warning';
  expandable: boolean;
  expanded: boolean;
  onToggle: () => void;
}) {
  const body = (
    <>
      <span className="flex size-3.5 shrink-0 items-center justify-center">{icon}</span>
      {color ? <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: color }} aria-hidden /> : null}
      <span className="shrink-0 font-medium text-fg">{who}</span>
      <span className="min-w-0 flex-1 truncate font-mono text-2xs text-fg-muted" title={what}>{what}</span>
      {note ? <span className={cn('shrink-0 text-2xs', noteTone === 'warning' ? 'text-warning' : 'text-danger')}>{note}</span> : null}
    </>
  );
  const cls = 'flex w-full min-w-0 items-center gap-1.5 rounded-sm px-1 py-1 text-left text-xs';
  return expandable ? (
    <button type="button" aria-expanded={expanded} title="Show what it printed" onClick={onToggle} className={cn(cls, 'outline-none hover:bg-hover focus-visible:ring-2 focus-visible:ring-accent/40')}>
      {body}
    </button>
  ) : (
    <div className={cls}>{body}</div>
  );
}

function Output({ text }: { text: string }) {
  return (
    <pre className="mx-1 mb-1 max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-sm border border-border bg-surface px-2 py-1.5 font-mono text-2xs leading-relaxed text-fg-muted">
      {text}
    </pre>
  );
}
