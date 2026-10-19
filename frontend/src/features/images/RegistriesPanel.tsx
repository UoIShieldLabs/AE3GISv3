import { useState } from 'react';
import { AlertTriangle, Boxes, ChevronDown, ChevronRight, ExternalLink, MoreHorizontal, Plus, RefreshCw, Trash2 } from 'lucide-react';
import type { Registry } from '@/api/client';
import { displayNameFor } from '@/catalog/catalog';
import { Badge, Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, IconButton, Input } from '@/ui';
import { addRegistry, removeRegistry, syncRegistry } from './actions';
import { registrySummary } from './imagePolling';

const when = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

/** Docker Hub namespaces whose standard images join the catalog, and a form to add one. */
export function RegistriesPanel({ registries }: { registries: Registry[] }) {
  return (
    <div className="flex flex-col gap-2">
      {registries.map((reg) => <RegistryRow key={reg.id} registry={reg} />)}
      <AddRegistry first={registries.length === 0} />
    </div>
  );
}

function AddRegistry({ first }: { first: boolean }) {
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!url.trim() || busy) return;
    setBusy(true);
    if (await addRegistry(url.trim())) setUrl('');
    setBusy(false);
  };
  return (
    <form className="flex flex-col gap-1" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <div className="flex items-center gap-2">
        <div className="min-w-0 flex-1">
          <Input
            leading={<Boxes />}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://hub.docker.com/u/<namespace>"
            aria-label="Docker Hub namespace"
            className="h-7 text-xs"
          />
        </div>
        <Button type="submit" size="sm" variant="secondary" loading={busy} disabled={!url.trim()}>
          <Plus /> Add registry
        </Button>
      </div>
      {first ? (
        <p className="text-2xs text-fg-subtle">
          Load node images from a Docker Hub namespace. Only repos whose description starts with{' '}
          <span className="font-mono">[ae3gis]</span> are read, and their images must carry the AE3GIS labels (see docs/image-standard.md).
        </p>
      ) : null}
    </form>
  );
}

export function RegistryRow({ registry: reg }: { registry: Registry }) {
  const [open, setOpen] = useState(false);
  const syncing = !!reg.active_job;
  const failed = reg.last_job?.status === 'failed' ? reg.last_job.error : null;
  const rejected = reg.rejected ?? [];
  const warnings = reg.warnings ?? [];
  const pending = reg.pending ?? [];
  const loaded = reg.loaded ?? [];
  const step = reg.active_job?.steps.find((s) => s.status === 'running')?.message;
  return (
    <div className="rounded-md border border-border bg-surface-2/50 text-xs">
      <div className="flex items-center gap-3 px-3 py-2">
        <IconButton label={open ? 'Hide details' : 'Show details'} size="icon-xs" onClick={() => setOpen(!open)} disabled={!reg.synced_at}>
          {open ? <ChevronDown /> : <ChevronRight />}
        </IconButton>
        <Boxes className="size-4 shrink-0 text-fg-subtle" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium">{reg.namespace}</span>
            <Badge tone="outline">Docker Hub</Badge>
            <a href={reg.hub_url} target="_blank" rel="noreferrer" className="text-fg-subtle hover:text-fg" aria-label={`${reg.namespace} on Docker Hub`}>
              <ExternalLink className="size-3" />
            </a>
          </div>
          <div className="truncate text-2xs text-fg-subtle">
            {syncing
              ? (step ?? 'Waiting to sync…')
              : reg.synced_at
                ? <>{registrySummary(reg)} · {reg.skipped} of {reg.repositories} repos not marked · synced {when(reg.synced_at)}</>
                : 'Not synced yet'}
          </div>
          {failed ? <div className="truncate text-2xs text-danger">Last sync failed: {failed}</div> : null}
          {!syncing && (rejected.length || pending.length) ? (
            <div className="flex items-center gap-1 text-2xs text-warning">
              <AlertTriangle className="size-3" />
              {[rejected.length ? `${rejected.length} rejected` : null, pending.length ? `${pending.length} waiting for Docker Hub's pull limit` : null].filter(Boolean).join(' · ')}
            </div>
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
        <div className="flex flex-col gap-2 border-t border-border px-3 py-2">
          {loaded.length ? (
            <section>
              <h4 className="mb-1 text-2xs font-medium uppercase tracking-wide text-fg-subtle">Loaded</h4>
              <ul className="flex flex-col gap-1">
                {loaded.map((img) => (
                  <li key={img.ref} className="flex flex-wrap items-center gap-x-2">
                    <span className="font-medium">{img.name}</span>
                    <span className="text-fg-muted">{img.new_type ? 'new type' : 'variant of'} {displayNameFor(img.type)}</span>
                    <span className="font-mono text-2xs text-fg-subtle">{img.ref}</span>
                    {(img.platforms ?? []).map((p) => <Badge key={p} tone="outline" mono>{p}</Badge>)}
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            <p className="text-2xs text-fg-subtle">No images loaded.</p>
          )}
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
