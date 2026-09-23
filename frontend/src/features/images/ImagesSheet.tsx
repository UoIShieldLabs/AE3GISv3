import { useMemo, useState } from 'react';
import { AlertTriangle, GitBranch, Hammer, MoreHorizontal, RefreshCw, Search, Square, X } from 'lucide-react';
import type { ImageSource, ImageStatus } from '@/api/client';
import { getCatalog } from '@/catalog/catalog';
import { cn } from '@/lib/cn';
import { useAppStore } from '@/store';
import {
  Badge, Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
  IconButton, Input, Sheet, Spinner, Tabs, TabsList, TabsTrigger,
} from '@/ui';
import { JobLog } from '@/features/jobs/JobLog';
import { buildImages, cancelJob, syncSource } from './actions';
import { refreshImages } from './imagePolling';
import { ImageStatusBadge } from './ImageStatusBadge';
import { formatBytes, needsAttention } from './status';

type Filter = 'attention' | 'built' | 'all';

/** The node types offering each image, e.g. "Firewall" for nftables. */
function usedByTypes(): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const spec of Object.values(getCatalog()?.types ?? {})) {
    for (const ref of spec.images?.length ? spec.images : [spec.defaultImage]) {
      map.set(ref, [...(map.get(ref) ?? []), spec.displayName]);
    }
  }
  return map;
}

/** Images AE3GIS builds from Dockerfiles: status, builds, logs, and their sources. */
export function ImagesSheet() {
  const open = useAppStore((s) => s.imagesOpen);
  const setOpen = useAppStore((s) => s.setImagesOpen);
  const focus = useAppStore((s) => s.imagesFocus);
  const report = useAppStore((s) => s.images);
  const error = useAppStore((s) => s.imagesError);
  const [filter, setFilter] = useState<Filter>('built');
  const [query, setQuery] = useState('');
  const [picked, setPicked] = useState<string | null>(null);
  const selectedRef = picked ?? focus;

  const usedBy = useMemo(() => (report ? usedByTypes() : new Map<string, string[]>()), [report]);
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (report?.images ?? [])
      .filter((i) => i.stability !== 'hidden')
      .filter((i) => (filter === 'all' ? true : filter === 'built' ? i.kind === 'build' : needsAttention(i)))
      .filter((i) => !q || `${i.display_name} ${i.ref} ${i.description} ${(usedBy.get(i.ref) ?? []).join(' ')}`.toLowerCase().includes(q));
  }, [report, filter, query, usedBy]);
  const selected = report?.images.find((i) => i.ref === selectedRef) ?? null;
  const missing = (report?.images ?? []).filter((i) => i.kind === 'build' && (i.status === 'missing' || i.status === 'failed') && i.stability !== 'hidden');
  const stale = (report?.images ?? []).filter((i) => i.status === 'stale');
  const attention = (report?.images ?? []).filter(needsAttention).length;

  return (
    <Sheet
      open={open}
      onOpenChange={(o) => { setOpen(o); if (!o) setPicked(null); }}
      side="right"
      size="min(920px, 100vw)"
      title="Images"
      description="Node images AE3GIS builds from Dockerfiles, and where those come from."
      headerAction={<IconButton label="Refresh" size="icon-sm" onClick={() => void refreshImages()}><RefreshCw /></IconButton>}
      flush
    >
      {!report ? (
        <div className="flex justify-center py-10">{error ? <p className="text-xs text-danger">{error}</p> : <Spinner />}</div>
      ) : (
        <div className="flex h-full min-h-0 flex-col">
          <div className="flex flex-col gap-3 border-b border-border p-4">
            <HostLine host={report.host} />
            {report.sources.map((src) => <SourceRow key={src.name} source={src} />)}
          </div>

          <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-2">
            <Tabs value={filter} onValueChange={(v) => setFilter(v as Filter)}>
              <TabsList variant="pills">
                <TabsTrigger value="built">Built here</TabsTrigger>
                <TabsTrigger value="attention">Needs attention{attention ? ` (${attention})` : ''}</TabsTrigger>
                <TabsTrigger value="all">All</TabsTrigger>
              </TabsList>
            </Tabs>
            <Input leading={<Search />} placeholder="Filter…" value={query} onChange={(e) => setQuery(e.target.value)} className="h-7 w-44 text-xs" />
            <div className="ml-auto flex items-center gap-1">
              {stale.length ? <Button size="sm" variant="secondary" onClick={() => void buildImages(stale.map((i) => i.ref))}><RefreshCw /> Rebuild {stale.length} out of date</Button> : null}
              {missing.length ? <Button size="sm" variant="secondary" onClick={() => void buildImages(missing.map((i) => i.ref))}><Hammer /> Build {missing.length} missing</Button> : null}
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-auto">
            {visible.length === 0 ? (
              <p className="p-8 text-center text-xs text-fg-muted">{filter === 'attention' ? 'Every image is ready.' : 'No images match.'}</p>
            ) : (
              <table className="w-full text-xs">
                <thead className="sticky top-0 z-10 bg-surface text-left text-2xs uppercase tracking-wide text-fg-subtle">
                  <tr className="border-b border-border">
                    <th className="px-4 py-1.5 font-medium">Image</th>
                    <th className="px-2 py-1.5 font-medium">Status</th>
                    <th className="px-2 py-1.5 font-medium">Built</th>
                    <th className="px-2 py-1.5 text-right font-medium">Size</th>
                    <th className="w-32 px-4" />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((img) => (
                    <ImageRow key={img.ref} image={img} usedBy={usedBy.get(img.ref) ?? []} selected={img.ref === selectedRef} onSelect={() => setPicked(img.ref === selectedRef ? null : img.ref)} />
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {selected ? <Details image={selected} onClose={() => setPicked(null)} /> : null}
        </div>
      )}
    </Sheet>
  );
}

function HostLine({ host }: { host: { platform: string; can_build: boolean; detail: string } }) {
  if (host.can_build) {
    return <p className="text-xs text-fg-muted">Builds run on this host (<span className="font-mono">{host.platform}</span>) with BuildKit.</p>;
  }
  return (
    <div className="flex items-start gap-2 rounded-md bg-danger-soft p-2.5 text-xs text-danger">
      <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
      <span>This host can't build images: {host.detail}. Images already built still deploy.</span>
    </div>
  );
}

function SourceRow({ source }: { source: ImageSource }) {
  const syncing = !!source.active_job;
  const failed = source.last_job?.status === 'failed' ? source.last_job.error : null;
  return (
    <div className="flex items-center gap-3 rounded-md border border-border bg-surface-2/50 px-3 py-2 text-xs">
      <GitBranch className="size-4 shrink-0 text-fg-subtle" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">{source.name}</span>
          {source.ref ? <Badge tone="outline" mono>{source.ref}</Badge> : null}
          {source.revision ? <span className="font-mono text-2xs text-fg-subtle">@ {source.revision.slice(0, 12)}</span> : null}
        </div>
        <div className="truncate text-2xs text-fg-subtle">{source.url ?? source.path} · {source.detail}</div>
        {failed ? <div className="truncate text-2xs text-danger">Last sync failed: {failed}</div> : null}
      </div>
      {source.kind === 'git' ? (
        <Button size="sm" variant="secondary" disabled={!source.can_sync} loading={syncing} onClick={() => void syncSource(source.name)} title={source.can_sync ? 'Fetch the latest Dockerfiles' : source.detail}>
          <RefreshCw /> {source.revision ? 'Check for updates' : 'Sync'}
        </Button>
      ) : null}
    </div>
  );
}

function ImageRow({ image, usedBy, selected, onSelect }: { image: ImageStatus; usedBy: string[]; selected: boolean; onSelect: () => void }) {
  const built = image.kind === 'build';
  const job = image.active_job;
  const created = image.created ? new Date(image.created).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : null;
  return (
    <tr onClick={onSelect} className={cn('cursor-pointer border-b border-border align-top hover:bg-hover', selected && 'bg-active')}>
      <td className="px-4 py-2">
        <div className="flex items-center gap-1.5">
          <span className="font-medium">{image.display_name}</span>
          {image.stability === 'experimental' ? <Badge tone="outline">experimental</Badge> : null}
        </div>
        <div className="font-mono text-2xs text-fg-subtle">{image.ref}</div>
        {usedBy.length ? <div className="text-2xs text-fg-subtle">{usedBy.join(', ')}</div> : null}
      </td>
      <td className="px-2 py-2">
        <ImageStatusBadge image={image} />
        {job ? <div className="mt-1 max-w-56 truncate text-2xs text-fg-subtle">{job.steps.find((s) => s.status === 'running')?.message ?? 'Queued'}</div> : null}
      </td>
      <td className="px-2 py-2 text-2xs text-fg-muted">
        {created ?? '—'}
        {image.built_revision ? <div className="font-mono text-fg-subtle">{image.built_revision.slice(0, 12)}</div> : null}
      </td>
      <td className="px-2 py-2 text-right text-2xs tabular text-fg-muted">{formatBytes(image.size)}</td>
      <td className="px-4 py-2 text-right" onClick={(e) => e.stopPropagation()}>
        {built ? <RowActions image={image} /> : null}
      </td>
    </tr>
  );
}

function RowActions({ image }: { image: ImageStatus }) {
  const job = image.active_job;
  if (job) {
    return <Button size="xs" variant="ghost" onClick={() => void cancelJob(job.id, `Build of ${image.display_name}`)}><Square /> Cancel</Button>;
  }
  const present = !['missing', 'failed', 'unavailable'].includes(image.status);
  return (
    <div className="flex items-center justify-end gap-1">
      <Button size="xs" variant={image.status === 'stale' || !present ? 'secondary' : 'ghost'} disabled={image.status === 'unavailable'} onClick={() => void buildImages([image.ref])}>
        {present ? <><RefreshCw /> Rebuild</> : <><Hammer /> Build</>}
      </Button>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <IconButton label="More" size="icon-xs" disabled={image.status === 'unavailable'}><MoreHorizontal /></IconButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => void buildImages([image.ref], { fresh: true })}>
            <RefreshCw /> Rebuild from scratch
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

function Details({ image, onClose }: { image: ImageStatus; onClose: () => void }) {
  const job = image.active_job ?? image.last_job;
  return (
    <div className="flex h-[42%] min-h-48 shrink-0 flex-col gap-2 border-t border-border bg-surface p-4">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-semibold">{image.display_name}</span>
            <ImageStatusBadge image={image} />
          </div>
          <p className="text-2xs text-fg-muted">{image.reason}{image.description ? ` · ${image.description}` : ''}</p>
          {image.kind === 'build' ? (
            <p className="font-mono text-2xs text-fg-subtle">
              source {image.source} · expected {image.expected_fingerprint?.slice(0, 12) ?? '—'} · built {image.built_fingerprint?.slice(0, 12) ?? '—'}
            </p>
          ) : null}
        </div>
        <IconButton label="Close details" size="icon-xs" onClick={onClose}><X /></IconButton>
      </div>
      {job ? (
        <>
          <div className="flex items-center gap-2 text-2xs text-fg-subtle">
            <span>{image.active_job ? 'Current build' : 'Last build'}:</span>
            {job.steps.map((s) => (
              <Badge key={s.name} tone={s.status === 'succeeded' ? 'success' : s.status === 'failed' ? 'danger' : s.status === 'running' ? 'info' : 'neutral'} dot={s.status === 'running' ? 'pulse' : undefined}>
                {s.name}
              </Badge>
            ))}
          </div>
          <JobLog key={job.id} jobId={job.id} className="min-h-0 flex-1" emptyText="Waiting for output…" />
        </>
      ) : (
        <p className="text-2xs text-fg-subtle">{image.kind === 'build' ? 'Not built yet. It is built on first deploy, or now with Build.' : 'Pulled from its registry when a deploy needs it.'}</p>
      )}
    </div>
  );
}
