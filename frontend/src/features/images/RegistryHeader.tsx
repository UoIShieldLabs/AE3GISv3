import { useState } from 'react';
import { AlertTriangle, Boxes, ChevronDown, ChevronRight, ExternalLink, MoreHorizontal, Plus, RefreshCw, Trash2 } from 'lucide-react';
import type { Registry } from '@/api/client';
import { Badge, Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, IconButton, Input } from '@/ui';
import { addRegistry, removeRegistry, syncRegistry } from './actions';
import { registrySummary } from './imagePolling';

const when = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** Add a Docker Hub namespace whose standard images join the catalog. */
export function AddRegistry({ onAdded }: { onAdded?: (namespace: string) => void }) {
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!url.trim() || busy) return;
    setBusy(true);
    const reg = await addRegistry(url.trim());
    setBusy(false);
    if (reg) {
      setUrl('');
      onAdded?.(reg.namespace);
    }
  };
  return (
    <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <div className="flex items-center gap-2">
        <div className="min-w-0 flex-1">
          <Input
            leading={<Boxes />}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://hub.docker.com/u/<namespace>"
            aria-label="Docker Hub namespace"
            className="h-8 text-xs"
            autoFocus
          />
        </div>
        <Button type="submit" size="sm" loading={busy} disabled={!url.trim()}>
          <Plus /> Add registry
        </Button>
      </div>
      <p className="text-2xs text-fg-subtle">
        AE3GIS reads the repos whose Docker Hub description starts with <span className="font-mono">[ae3gis]</span>. Their images
        carry the AE3GIS labels (docs/image-standard.md) and join the catalog as node types or variants; deploys pull them.
      </p>
    </form>
  );
}

/** The selected registry: what its last sync loaded, Sync / Remove, and its problems on demand. */
export function RegistryHeader({ registry: reg }: { registry: Registry }) {
  const [open, setOpen] = useState(false);
  const syncing = !!reg.active_job;
  const failed = reg.last_job?.status === 'failed' ? reg.last_job.error : null;
  const rejected = reg.rejected ?? [];
  const warnings = reg.warnings ?? [];
  const pending = reg.pending ?? [];
  const step = reg.active_job?.steps.find((s) => s.status === 'running')?.message;
  const problems = [
    rejected.length ? `${rejected.length} rejected` : null,
    pending.length ? `${pending.length} waiting for Docker Hub's pull limit` : null,
    warnings.length ? plural(warnings.length, 'warning') : null,
  ].filter(Boolean);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-start gap-3">
        <Boxes className="mt-0.5 size-4 shrink-0 text-fg-subtle" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">{reg.namespace}</span>
            <Badge tone="outline">Docker Hub</Badge>
            <a href={reg.hub_url} target="_blank" rel="noreferrer" className="text-fg-subtle hover:text-fg" aria-label={`${reg.namespace} on Docker Hub`}>
              <ExternalLink className="size-3" />
            </a>
          </div>
          <div className="text-2xs text-fg-subtle">
            {syncing
              ? (step ?? 'Waiting to sync…')
              : reg.synced_at
                ? <>{registrySummary(reg)} · {reg.skipped} of {reg.repositories} repos not marked · synced {when(reg.synced_at)}</>
                : 'Not synced yet'}
          </div>
          {failed ? <div className="text-2xs text-danger">Last sync failed: {failed}</div> : null}
          {!syncing && problems.length ? (
            <button type="button" className="mt-0.5 flex items-center gap-1 text-2xs text-warning hover:underline" aria-expanded={open} onClick={() => setOpen(!open)}>
              <AlertTriangle className="size-3" /> {problems.join(' · ')}
              {open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
            </button>
          ) : null}
        </div>
        <Button size="sm" variant="secondary" loading={syncing} onClick={() => void syncRegistry(reg)} title="Re-read the namespace">
          <RefreshCw /> Sync
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <IconButton label="More" size="icon-xs"><MoreHorizontal /></IconButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem disabled={syncing} onSelect={() => void removeRegistry(reg)} className="text-danger">
              <Trash2 /> Remove registry
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {open ? (
        <div className="flex flex-col gap-2 rounded-md border border-border bg-surface-2/50 px-3 py-2 text-xs">
          {rejected.length ? (
            <section>
              <h4 className="mb-1 text-2xs font-medium uppercase tracking-wide text-fg-subtle">Rejected</h4>
              <ul className="flex flex-col gap-1">
                {rejected.map((r) => (
                  <li key={r.repo}>
                    <span className="font-mono">{r.repo}:{r.tag}</span>
                    <ul className="ml-4 list-disc text-2xs text-danger">
                      {r.reasons.map((reason) => <li key={reason}>{reason}</li>)}
                    </ul>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {pending.length ? (
            <p className="text-2xs text-fg-muted">
              Not read yet ({reg.pulls_remaining ?? 0} Docker Hub pulls left this hour): <span className="font-mono">{pending.join(', ')}</span>. Sync again later.
            </p>
          ) : null}
          {warnings.length ? (
            <section>
              <h4 className="mb-1 text-2xs font-medium uppercase tracking-wide text-fg-subtle">Warnings</h4>
              <ul className="ml-4 list-disc text-2xs text-warning">
                {warnings.map((w) => <li key={w}>{w}</li>)}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
