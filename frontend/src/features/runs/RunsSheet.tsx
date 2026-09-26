import { useCallback, useEffect, useState } from 'react';
import { Activity, Download, Plus, Radio, RefreshCw } from 'lucide-react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { Badge, Button, EmptyState, IconButton, Sheet } from '@/ui';
import { downloadPcap, openCaptureTab } from '@/features/capture/actions';
import { formatBytes } from '@/features/capture/packetBuffer';
import { exportTrafficRun, openTrafficPanel, openTrafficRun } from '@/features/traffic/actions';

function StatusBadge({ status, live }: { status: string; live: boolean }) {
  if (live) return <Badge tone="success" dot="pulse">Running</Badge>;
  if (status === 'failed') return <Badge tone="danger">Failed</Badge>;
  if (status === 'cancelled') return <Badge tone="warning">Cancelled</Badge>;
  return <Badge>Done</Badge>;
}

const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'medium' }) : '–');

/** Every capture and traffic run of the loaded topology, newest first. */
export function RunsSheet() {
  const { open, backendId, activityKey } = useAppShallow((s) => ({ open: s.runsOpen, backendId: s.backendId, activityKey: s.activity.map((a) => a.job_id).join(',') }));
  const setOpen = useAppStore((s) => s.setRunsOpen);
  const [captures, setCaptures] = useState<api.Capture[] | null>(null);
  const [runs, setRuns] = useState<api.TrafficRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!backendId) return;
    Promise.all([api.listCaptures(backendId), api.listTrafficRuns(backendId)])
      .then(([c, r]) => { setCaptures(c); setRuns(r); setError(null); })
      .catch((err: unknown) => setError(api.errorMessage(err)));
  }, [backendId]);

  // Refresh when opened, and when something starts or finishes while open.
  useEffect(() => { if (open) refresh(); }, [open, refresh, activityKey]);

  const show = (fn: () => void) => { fn(); setOpen(false); };

  return (
    <Sheet
      open={open}
      onOpenChange={setOpen}
      side="right"
      size="min(760px, 100vw)"
      title="Captures & traffic runs"
      description="Everything recorded on this topology. Pcaps, samples and each run's environment are kept on the server."
      headerAction={<IconButton label="Refresh" size="icon-sm" onClick={refresh}><RefreshCw /></IconButton>}
    >
      {!backendId ? (
        <EmptyState title="Save the topology first" description="Captures and runs belong to a saved, deployed topology." />
      ) : (
        <div className="flex flex-col gap-6 text-xs">
          {error ? <div className="rounded-md bg-danger-soft px-3 py-2 text-danger">{error}</div> : null}
          <section>
            <div className="mb-2 flex items-center gap-2">
              <Activity className="size-3.5 text-fg-muted" aria-hidden />
              <h3 className="font-medium text-fg">Traffic runs</h3>
              <Button size="xs" variant="ghost" className="ml-auto" onClick={() => show(() => openTrafficPanel())}><Plus /> New run</Button>
            </div>
            {runs?.length ? (
              <ul className="divide-y divide-border rounded-md border border-border">
                {runs.map((r) => {
                  const result = r.result as { stopped_by?: string; duration_s?: number } | null | undefined;
                  return (
                    <li key={r.id} className="flex items-center gap-3 px-3 py-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate font-medium text-fg">{r.label || 'Traffic run'}</span>
                          <StatusBadge status={r.status} live={r.live} />
                        </div>
                        <div className="truncate text-2xs text-fg-muted">
                          {when(r.job.started_at ?? r.job.created_at)} · {r.flows.length} flow(s)
                          {result?.duration_s ? ` · ${result.duration_s.toFixed(0)}s` : ''}
                          {r.status === 'failed' && r.job.error ? ` · ${r.job.error}` : ''}
                        </div>
                      </div>
                      <Button size="xs" variant="secondary" onClick={() => show(() => openTrafficRun(r.id, r.label || 'Traffic run'))}>Open</Button>
                      <IconButton label="Export (.zip)" size="icon-sm" disabled={r.live} onClick={() => exportTrafficRun(r.id)}><Download /></IconButton>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-fg-subtle">{runs ? 'No traffic runs yet.' : 'Loading…'}</p>
            )}
          </section>
          <section>
            <div className="mb-2 flex items-center gap-2">
              <Radio className="size-3.5 text-fg-muted" aria-hidden />
              <h3 className="font-medium text-fg">Captures</h3>
              <span className="ml-auto text-2xs text-fg-subtle">Start one from a link or device (right-click).</span>
            </div>
            {captures?.length ? (
              <ul className="divide-y divide-border rounded-md border border-border">
                {captures.map((c) => (
                  <li key={c.id} className="flex items-center gap-3 px-3 py-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate font-medium text-fg">{c.label || `${c.endpoint.machine} · ${c.endpoint.interface}`}</span>
                        <span className="shrink-0 font-mono text-2xs text-fg-subtle">{c.endpoint.interface}</span>
                        {c.filter ? <Badge mono tone="outline">{c.filter}</Badge> : null}
                        <StatusBadge status={c.status} live={c.live} />
                      </div>
                      <div className="truncate text-2xs text-fg-muted">
                        {when(c.job.started_at ?? c.job.created_at)} · {(c.stats.packets ?? 0).toLocaleString()} packets · {formatBytes(c.stats.file_bytes)}
                        {c.status === 'failed' && c.job.error ? ` · ${c.job.error}` : ''}
                      </div>
                    </div>
                    <Button size="xs" variant="secondary" onClick={() => show(() => openCaptureTab(c.id, c.label || 'Capture'))}>Open</Button>
                    <IconButton label="Download .pcap" size="icon-sm" disabled={!c.stats.file_bytes} onClick={() => downloadPcap(c.id)}><Download /></IconButton>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-fg-subtle">{captures ? 'No captures yet.' : 'Loading…'}</p>
            )}
          </section>
        </div>
      )}
    </Sheet>
  );
}
