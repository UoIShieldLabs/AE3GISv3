import { useMemo, useState } from 'react';
import { AlertTriangle, Boxes, GitBranch, Globe, Hammer, Layers, MoreHorizontal, Plus, RefreshCw, Search, Square, X } from 'lucide-react';
import type { ImageSource, ImagesReport, ImageStatus } from '@/api/client';
import { getCatalog } from '@/catalog/catalog';
import { cn } from '@/lib/cn';
import { useAppStore } from '@/store';
import {
  Badge, Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
  IconButton, Input, Sheet, Spinner,
} from '@/ui';
import { JobLog } from '@/features/jobs/JobLog';
import { buildImages, cancelJob, syncSource } from './actions';
import { refreshImages } from './imagePolling';
import { ImageStatusBadge } from './ImageStatusBadge';
import { AddRegistry, RegistryHeader } from './RegistryHeader';
import { imagesFor, sourceEntries, sourceKeyOf, type SourceEntry, type SourceKey } from './sources';
import { formatBytes, needsAttention } from './status';

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

/** Node images by where they come from: the Docker Hub registries the user
 *  added, sources AE3GIS builds from on this host, and the built-in catalog's
 *  public images. Sources on the left, the selected one's images on the right. */
export function ImagesSheet() {
  const open = useAppStore((s) => s.imagesOpen);
  const setOpen = useAppStore((s) => s.setImagesOpen);
  const focus = useAppStore((s) => s.imagesFocus);
  const report = useAppStore((s) => s.images);
  const error = useAppStore((s) => s.imagesError);
  // What the user chose, tied to the image the sheet was asked to show: a new
  // request (openImages(ref) from the inspector, a banner, a toast) wins.
  const [choice, setChoice] = useState<{ key: SourceKey; focus: string | null } | null>(null);
  const [pick, setPick] = useState<{ ref: string | null; focus: string | null } | null>(null);
  const chosen = choice && choice.focus === focus ? choice.key : null;
  const picked = pick && pick.focus === focus ? pick.ref : undefined;

  const close = (o: boolean) => {
    setOpen(o);
    if (!o) { setChoice(null); setPick(null); }
  };

  return (
    <Sheet
      open={open}
      onOpenChange={close}
      side="right"
      size="min(980px, 100vw)"
      title="Images"
      description="Node images by where they come from: your Docker Hub registries, builds on this host, and public images."
      headerAction={<IconButton label="Refresh" size="icon-sm" onClick={() => void refreshImages()}><RefreshCw /></IconButton>}
      flush
    >
      {!report ? (
        <div className="flex justify-center py-10">{error ? <p className="text-xs text-danger">{error}</p> : <Spinner />}</div>
      ) : (
        <Browser
          report={report}
          focus={focus}
          chosen={chosen}
          onChoose={(key) => { setChoice({ key, focus }); setPick({ ref: null, focus }); }}
          picked={picked}
          onPick={(ref) => setPick({ ref, focus })}
        />
      )}
    </Sheet>
  );
}

function Browser({ report, focus, chosen, onChoose, picked, onPick }: {
  report: ImagesReport;
  focus: string | null;
  chosen: SourceKey | null;
  onChoose: (key: SourceKey) => void;
  /** undefined: nothing picked yet (the focused image, if any, is shown). */
  picked: string | null | undefined;
  onPick: (ref: string | null) => void;
}) {
  const entries = useMemo(() => sourceEntries(report), [report]);
  // Opened on an image (inspector, banner, toast): its source, until another is chosen.
  const focusImage = focus ? report.images.find((i) => i.ref === focus) : undefined;
  const wanted: SourceKey = chosen ?? (focusImage ? sourceKeyOf(focusImage, report) : 'all');
  // A source that went away (a removed registry) falls back to every image.
  const selected: SourceKey = wanted === 'add-registry' || entries.some((e) => e.key === wanted) ? wanted : 'all';
  const selectedRef = picked !== undefined ? picked : chosen ? null : focus;

  return (
    <div className="grid h-full min-h-0 grid-cols-[220px_minmax(0,1fr)]">
      <SourceNav entries={entries} selected={selected} onSelect={onChoose} />
      {selected === 'add-registry' ? (
        <div className="flex flex-col gap-3 overflow-auto p-4">
          <h3 className="text-sm font-semibold">Add a Docker Hub registry</h3>
          <AddRegistry onAdded={(ns) => onChoose(`registry:${ns}`)} />
        </div>
      ) : (
        <SourcePane key={selected} report={report} source={selected} selectedRef={selectedRef} onPick={onPick} />
      )}
    </div>
  );
}

// ── Left: the sources ─────────────────────────────────────────────────

function SourceNav({ entries, selected, onSelect }: { entries: SourceEntry[]; selected: SourceKey; onSelect: (key: SourceKey) => void }) {
  const all = entries.find((e) => e.group === 'all');
  const registries = entries.filter((e) => e.group === 'registry');
  const builds = entries.filter((e) => e.group === 'build');
  const pub = entries.find((e) => e.group === 'public');
  return (
    <nav aria-label="Image sources" className="flex min-h-0 flex-col gap-3 overflow-auto border-r border-border bg-surface-2/40 p-2 text-xs">
      {all ? <NavItem entry={all} icon={<Layers />} selected={selected === all.key} onSelect={onSelect} /> : null}
      <NavGroup
        title="Docker Hub"
        action={<IconButton label="Add registry" size="icon-xs" onClick={() => onSelect('add-registry')}><Plus /></IconButton>}
      >
        {registries.map((e) => <NavItem key={e.key} entry={e} icon={<Boxes />} selected={selected === e.key} onSelect={onSelect} />)}
        {registries.length === 0 ? (
          <button type="button" onClick={() => onSelect('add-registry')} className={cn('flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-fg-muted hover:bg-hover', selected === 'add-registry' && 'bg-active text-fg')}>
            <Plus className="size-3.5" /> Add a registry
          </button>
        ) : null}
      </NavGroup>
      {builds.length ? (
        <NavGroup title="Built on this host">
          {builds.map((e) => <NavItem key={e.key} entry={e} icon={<GitBranch />} selected={selected === e.key} onSelect={onSelect} />)}
        </NavGroup>
      ) : null}
      {pub ? (
        <NavGroup title="Public">
          <NavItem entry={pub} icon={<Globe />} selected={selected === pub.key} onSelect={onSelect} />
        </NavGroup>
      ) : null}
    </nav>
  );
}

function NavGroup({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex h-6 items-center justify-between px-2 text-2xs font-medium uppercase tracking-wide text-fg-subtle">
        {title}
        {action}
      </div>
      {children}
    </div>
  );
}

function NavItem({ entry, icon, selected, onSelect }: { entry: SourceEntry; icon: React.ReactNode; selected: boolean; onSelect: (key: SourceKey) => void }) {
  const flag = entry.warning ? 'has problems' : entry.attention ? `${entry.attention} need a build` : null;
  return (
    <button
      type="button"
      onClick={() => onSelect(entry.key)}
      aria-current={selected ? 'true' : undefined}
      className={cn('flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-hover [&_svg]:size-3.5 [&_svg]:shrink-0 [&_svg]:text-fg-subtle', selected && 'bg-active')}
    >
      {icon}
      <span className="min-w-0 flex-1 truncate">{entry.label}</span>
      {entry.busy ? <Spinner className="size-3" /> : flag ? <span title={flag} aria-label={flag} className="size-1.5 shrink-0 rounded-full bg-warning" /> : null}
      <span className="tabular text-2xs text-fg-subtle">{entry.count}</span>
    </button>
  );
}

// ── Right: the selected source ────────────────────────────────────────

function SourcePane({ report, source, selectedRef, onPick }: { report: ImagesReport; source: SourceKey; selectedRef: string | null; onPick: (ref: string | null) => void }) {
  const [query, setQuery] = useState('');
  const [attentionOnly, setAttentionOnly] = useState(false);
  // The catalog changes with the report (a registry sync adds images).
  const usedBy = useMemo(() => (report ? usedByTypes() : new Map<string, string[]>()), [report]);
  const images = useMemo(() => imagesFor(report, source), [report, source]);
  const attention = images.filter(needsAttention);
  const missing = images.filter((i) => i.kind === 'build' && (i.status === 'missing' || i.status === 'failed'));
  const stale = images.filter((i) => i.status === 'stale');
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return images
      .filter((i) => !attentionOnly || needsAttention(i))
      .filter((i) => !q || `${i.display_name} ${i.ref} ${i.description} ${(usedBy.get(i.ref) ?? []).join(' ')}`.toLowerCase().includes(q));
  }, [images, attentionOnly, query, usedBy]);
  const selected = images.find((i) => i.ref === selectedRef) ?? null;
  const registry = source.startsWith('registry:') ? (report.registries ?? []).find((r) => `registry:${r.namespace}` === source) : undefined;
  const buildSource = source.startsWith('build:') ? report.sources.find((s) => `build:${s.name}` === source) : undefined;

  return (
    <div className="flex min-h-0 flex-col">
      <div className="border-b border-border p-4">
        {registry ? <RegistryHeader registry={registry} />
          : buildSource ? <BuildSourceHeader source={buildSource} host={report.host} />
          : source === 'public' ? <PaneTitle icon={<Globe />} title="Public images" detail="Upstream images the built-in catalog lists, pulled from Docker Hub on first deploy." />
          : <PaneTitle icon={<Layers />} title="All images" detail="Every node image: from your Docker Hub registries, built on this host, and public images." />}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-2">
        <Input leading={<Search />} placeholder="Filter…" value={query} onChange={(e) => setQuery(e.target.value)} className="h-7 w-48 text-xs" />
        {attention.length ? (
          <Button size="sm" variant={attentionOnly ? 'secondary' : 'ghost'} aria-pressed={attentionOnly} onClick={() => setAttentionOnly(!attentionOnly)}>
            <AlertTriangle /> Needs a build ({attention.length})
          </Button>
        ) : null}
        <div className="ml-auto flex items-center gap-1">
          {stale.length ? <Button size="sm" variant="secondary" onClick={() => void buildImages(stale.map((i) => i.ref))}><RefreshCw /> Rebuild {stale.length} out of date</Button> : null}
          {missing.length ? <Button size="sm" variant="secondary" onClick={() => void buildImages(missing.map((i) => i.ref))}><Hammer /> Build {missing.length} missing</Button> : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {visible.length === 0 ? (
          <p className="p-8 text-center text-xs text-fg-muted">{emptyText(source, images.length, !!registry?.active_job)}</p>
        ) : (
          <table className="w-full text-xs">
            <thead className="sticky top-0 z-10 bg-surface text-left text-2xs uppercase tracking-wide text-fg-subtle">
              <tr className="border-b border-border">
                <th className="px-4 py-1.5 font-medium">Image</th>
                <th className="px-2 py-1.5 font-medium">Status</th>
                <th className="px-2 py-1.5 text-right font-medium">Size</th>
                <th className="w-32 px-4" />
              </tr>
            </thead>
            <tbody>
              {visible.map((img) => (
                <ImageRow key={img.ref} image={img} usedBy={usedBy.get(img.ref) ?? []} selected={img.ref === selectedRef} onSelect={() => onPick(img.ref === selectedRef ? null : img.ref)} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected ? <Details image={selected} onClose={() => onPick(null)} /> : null}
    </div>
  );
}

function emptyText(source: SourceKey, total: number, syncing: boolean): string {
  if (total > 0) return 'No images match.';
  if (source.startsWith('registry:')) return syncing ? 'Reading the namespace…' : 'No images loaded from this registry. Repos need the [ae3gis] description and the AE3GIS labels.';
  return 'No images here.';
}

function PaneTitle({ icon, title, detail }: { icon: React.ReactNode; title: string; detail: string }) {
  return (
    <div className="flex items-start gap-3 [&_svg]:mt-0.5 [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-fg-subtle">
      {icon}
      <div>
        <div className="text-sm font-semibold">{title}</div>
        <p className="text-2xs text-fg-subtle">{detail}</p>
      </div>
    </div>
  );
}

function BuildSourceHeader({ source, host }: { source: ImageSource; host: ImagesReport['host'] }) {
  const syncing = !!source.active_job;
  const failed = source.last_job?.status === 'failed' ? source.last_job.error : null;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-start gap-3">
        <GitBranch className="mt-0.5 size-4 shrink-0 text-fg-subtle" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">{source.name}</span>
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
      <HostLine host={host} />
    </div>
  );
}

function HostLine({ host }: { host: ImagesReport['host'] }) {
  if (host.can_build) {
    return <p className="text-2xs text-fg-muted">AE3GIS builds these images on this host (<span className="font-mono">{host.platform}</span>) with BuildKit, on first deploy or with Build.</p>;
  }
  return (
    <div className="flex items-start gap-2 rounded-md bg-danger-soft p-2.5 text-xs text-danger">
      <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
      <span>This host can't build images: {host.detail}. Images already built still deploy.</span>
    </div>
  );
}

// ── Image rows and details ────────────────────────────────────────────

function ImageRow({ image, usedBy, selected, onSelect }: { image: ImageStatus; usedBy: string[]; selected: boolean; onSelect: () => void }) {
  const built = image.kind === 'build';
  const job = image.active_job;
  const created = built && image.created ? new Date(image.created).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : null;
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
        {!job && created ? <div className="mt-1 text-2xs text-fg-subtle">built {created}</div> : null}
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
