import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Boxes, Clock, Copy, Ellipsis, EyeOff, FilePlus2, FolderOpen, GraduationCap, LayoutTemplate, Plus, RefreshCw, Server, Share2, Trash2, Upload, Users,
} from 'lucide-react';
import * as api from '@/api/client';
import { createNewTopology } from '@/features/deployment/actions';
import {
  Badge, Button, Dialog, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
  EmptyState, IconButton, Spinner, Tooltip, toast,
} from '@/ui';
import { cn } from '@/lib/cn';
import { AppearanceMenu } from '@/shell/AppearanceMenu';
import { UserMenu } from '@/shell/UserMenu';
import { LabsDialog } from '@/features/system/LabsDialog';
import { ImagesSheet } from '@/features/images/ImagesSheet';
import { ClassSheet } from '@/features/class/ClassSheet';
import { useCan, useIsStudent } from '@/lib/permissions';
import { useAppStore } from '@/store';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

const STATUS_TONE: Record<string, 'success' | 'neutral' | 'warning' | 'danger'> = {
  deployed: 'success', idle: 'neutral', deploying: 'warning', destroying: 'warning', error: 'danger',
};

function SectionTitle({ icon, children, aside }: { icon: React.ReactNode; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-fg-muted [&>svg]:size-3.5">
      {icon} {children}
      {aside ? <span className="ml-auto font-normal normal-case tracking-normal text-fg-subtle">{aside}</span> : null}
    </h2>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">{children}</ul>;
}

/** A quiet state on a card's date line: a dot and a word (Published, Updated). */
function Flag({ tone, title, children }: { tone: 'accent' | 'warning'; title?: string; children: React.ReactNode }) {
  return (
    <span title={title} className={cn('flex min-w-0 items-center gap-1', tone === 'accent' ? 'text-accent' : 'text-warning')}>
      <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-current" />
      <span className="truncate">{children}</span>
    </span>
  );
}

/** One topology: name, when, status, one primary action and a "⋯" menu.
 *  Everything on one line truncates, so long names never push the card wider. */
function TopologyCard({ t, status = t.status, onOpen, marker, flags, primary, menu }: {
  t: api.TopologySummary;
  /** Shown instead of the topology's own (a lesson shows its copy's). */
  status?: string;
  onOpen: () => void;
  /** A small icon after the name. */
  marker?: React.ReactNode;
  /** `Flag`s after the date. */
  flags?: React.ReactNode;
  primary: React.ReactNode;
  /** Items of the "⋯" menu. */
  menu?: React.ReactNode;
}) {
  return (
    <li className="group flex min-w-0 flex-col gap-2 rounded-xl border border-border bg-surface p-4 shadow-sm transition-colors hover:border-border-strong">
      <div className="flex items-start justify-between gap-2">
        <button type="button" onClick={onOpen} className="min-w-0 flex-1 text-left">
          <div className="flex min-w-0 items-center gap-1.5">
            <span className="truncate text-sm font-medium hover:text-accent" title={t.name}>{t.name}</span>
            {marker}
          </div>
          <div className="mt-0.5 flex min-w-0 items-center gap-2 text-2xs text-fg-muted">
            <span className="flex shrink-0 items-center gap-1"><Clock className="size-3" /> {formatDate(t.updated_at)}</span>
            {flags}
          </div>
        </button>
        <Badge tone={STATUS_TONE[status] ?? 'neutral'} dot={status === 'deployed' ? 'pulse' : true}>{status}</Badge>
      </div>
      <div className="mt-auto flex items-center gap-1 pt-1">
        {primary}
        {menu ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <IconButton label="More" size="icon-sm" className="ml-auto opacity-60 group-hover:opacity-100 data-[state=open]:opacity-100"><Ellipsis /></IconButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">{menu}</DropdownMenuContent>
          </DropdownMenu>
        ) : null}
      </div>
    </li>
  );
}

export function LibraryRoute() {
  const navigate = useNavigate();
  const [topologies, setTopologies] = useState<api.TopologySummary[] | null>(null);
  const [presets, setPresets] = useState<api.PresetSummary[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<api.TopologySummary | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [labsOpen, setLabsOpen] = useState(false);
  const [classOpen, setClassOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const user = useAppStore((s) => s.user);
  const accounts = useAppStore((s) => !!s.authRequired);
  const isStudent = useIsStudent();
  const canPublish = useCan('publish') && accounts;
  const canManageClass = useCan('manageClass') && accounts;
  const canManageImages = useCan('manageImages');
  const canManageHost = useCan('manageHost');

  const refresh = useCallback(async () => {
    try {
      const [t, p] = await Promise.all([api.listTopologies(), api.listPresets().catch(() => ({ presets: [] }))]);
      setTopologies(t.slice().sort((a, b) => b.updated_at.localeCompare(a.updated_at)));
      setPresets(p.presets);
    } catch (err) {
      setTopologies([]);
      toast.error('Could not load topologies', { description: api.errorMessage(err) });
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  // Sections: a student's own (copies included) and what the instructor
  // published; the instructor's own and, per student, the students'.
  const sections = useMemo(() => {
    const all = topologies ?? [];
    const published = isStudent ? all.filter((t) => t.published && t.owner?.id !== user?.id) : [];
    // A student's copy of a lesson is opened from the lesson's card; it shows
    // here only once the lesson is gone (unpublished or deleted).
    const lessonIds = new Set(published.map((t) => t.id));
    const mine = all.filter((t) =>
      isStudent ? t.owner?.id === user?.id && !(t.source_id && lessonIds.has(t.source_id)) : !t.owner,
    );
    const byStudent = new Map<string, api.TopologySummary[]>();
    if (!isStudent) {
      for (const t of all) {
        if (!t.owner) continue;
        const rows = byStudent.get(t.owner.username) ?? [];
        rows.push(t);
        byStudent.set(t.owner.username, rows);
      }
    }
    const names = new Map(all.map((t) => [t.id, t.name]));
    return { mine, published, byStudent: [...byStudent.entries()].sort(([a], [b]) => a.localeCompare(b)), names };
  }, [topologies, isStudent, user?.id]);

  const open = (id: string) => void navigate(`/t/${encodeURIComponent(id)}`);

  const startNew = () => {
    createNewTopology();
    void navigate('/t/draft');
  };

  const withBusy = async (id: string, fn: () => Promise<void>, failure: string) => {
    setBusyId(id);
    try {
      await fn();
    } catch (err) {
      toast.error(failure, { description: api.errorMessage(err) });
    } finally {
      setBusyId(null);
    }
  };

  const loadPreset = (id: string) =>
    void withBusy(id, async () => open((await api.loadPreset(id)).id), 'Could not load preset');

  const importFile = (file: File) =>
    void withBusy('import', async () => {
      const rec = await api.importJsonTopology(file);
      toast.success('Imported', { description: rec.name });
      open(rec.id);
    }, 'Import failed');

  /** A student's copy of a published topology (theirs if they made one). */
  const openCopy = (t: api.TopologySummary) =>
    void withBusy(t.id, async () => open((await api.copyTopology(t.id)).id), 'Could not open it');

  const duplicate = (t: api.TopologySummary) =>
    void withBusy(t.id, async () => {
      const rec = await api.copyTopology(t.id);
      toast.success('Duplicated', { description: rec.name });
      await refresh();
    }, 'Could not duplicate');

  const togglePublished = (t: api.TopologySummary, published: boolean) =>
    void withBusy(t.id, async () => {
      const rec = await api.setPublished(t.id, published);
      setTopologies((prev) => prev?.map((x) => (x.id === t.id ? { ...x, published: rec.published ?? published } : x)) ?? null);
      toast.success(published ? 'Published to students' : 'No longer published', { description: t.name });
    }, 'Could not change publishing');

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteTopology(deleteTarget.id);
      setTopologies((prev) => prev?.filter((t) => t.id !== deleteTarget.id) ?? null);
      toast.success('Deleted', { description: deleteTarget.name });
    } catch (err) {
      toast.error('Delete failed', { description: api.errorMessage(err) });
    }
    setDeleteTarget(null);
  };

  const ownMenu = (t: api.TopologySummary) => (
    <>
      {canPublish ? (
        t.published
          ? <DropdownMenuItem onSelect={() => togglePublished(t, false)}><EyeOff /> Stop publishing</DropdownMenuItem>
          : <DropdownMenuItem onSelect={() => togglePublished(t, true)}><Share2 /> Publish to students</DropdownMenuItem>
      ) : null}
      <DropdownMenuItem onSelect={() => duplicate(t)}><Copy /> Duplicate</DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem variant="danger" onSelect={() => setDeleteTarget(t)}><Trash2 /> Delete</DropdownMenuItem>
    </>
  );

  const ownFlags = (t: api.TopologySummary) => (
    <>
      {canPublish && t.published ? <Flag tone="accent" title="Students see it and open their own copy">Published</Flag> : null}
      {t.update_available ? <Flag tone="warning" title="Your instructor changed it since your copy was made">Updated</Flag> : null}
    </>
  );

  /** For the instructor: which lesson a student's topology was copied from. */
  const copyMarker = (t: api.TopologySummary) => {
    if (!t.source_id) return undefined;
    const from = sections.names.get(t.source_id);
    return (
      <Tooltip content={from ? `Copy of “${from}”` : 'Copy of a published topology'}>
        <span className="flex shrink-0 text-fg-subtle"><GraduationCap className="size-3.5" /></span>
      </Tooltip>
    );
  };

  const copyOf = (sourceId: string) => (topologies ?? []).find((t) => t.source_id === sourceId && t.owner?.id === user?.id);

  return (
    <div className="flex h-full flex-col bg-app">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-surface px-4">
        <span className="ae-brand text-sm font-semibold tracking-tight">AE3GIS</span>
        <span className="text-xs text-fg-muted">Topology library</span>
        <div className="ml-auto flex items-center gap-1">
          {canManageClass ? <Button size="sm" variant="ghost" onClick={() => setClassOpen(true)}><Users /> Class</Button> : null}
          {canManageImages ? <Button size="sm" variant="ghost" onClick={() => useAppStore.getState().openImages()}><Boxes /> Images</Button> : null}
          {canManageHost ? <Button size="sm" variant="ghost" onClick={() => setLabsOpen(true)}><Server /> Labs on this host</Button> : null}
          <IconButton label="Refresh" size="icon-sm" onClick={() => { setTopologies(null); void refresh(); }}><RefreshCw /></IconButton>
          <AppearanceMenu />
          <UserMenu />
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 p-6">
          <section className="flex flex-wrap items-center gap-2">
            <Button variant="primary" onClick={startNew}><Plus /> New topology</Button>
            <Button onClick={() => fileRef.current?.click()} loading={busyId === 'import'}><Upload /> Import JSON</Button>
            <input
              ref={fileRef}
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) importFile(f); e.target.value = ''; }}
            />
          </section>

          {topologies === null ? (
            <div className="flex justify-center py-10"><Spinner /></div>
          ) : (
            <>
              {isStudent ? (
                <section>
                  <SectionTitle icon={<GraduationCap />}>Lessons</SectionTitle>
                  {sections.published.length === 0 ? (
                    <p className="text-xs text-fg-subtle">No lessons yet.</p>
                  ) : (
                    <Grid>
                      {sections.published.map((t) => {
                        const mineCopy = copyOf(t.id);
                        return (
                          <TopologyCard
                            key={t.id}
                            t={t}
                            status={mineCopy?.status ?? 'idle'}
                            onOpen={() => openCopy(t)}
                            flags={mineCopy?.update_available ? <Flag tone="warning" title="Changed since you started; reset it from the editor">Updated</Flag> : null}
                            primary={
                              <Button size="sm" variant={mineCopy ? 'secondary' : 'primary'} onClick={() => openCopy(t)} loading={busyId === t.id} disabled={busyId !== null}>
                                {mineCopy ? 'Continue' : 'Start'}
                              </Button>
                            }
                            menu={mineCopy ? <DropdownMenuItem variant="danger" onSelect={() => setDeleteTarget(mineCopy)}><Trash2 /> Delete my copy</DropdownMenuItem> : undefined}
                          />
                        );
                      })}
                    </Grid>
                  )}
                </section>
              ) : null}

              <section>
                <SectionTitle icon={<FolderOpen />}>{accounts ? 'My topologies' : 'Saved topologies'}</SectionTitle>
                {sections.mine.length === 0 ? (
                  <EmptyState
                    icon={<FilePlus2 />}
                    title="No saved topologies"
                    description={isStudent ? 'Create one, or start a lesson.' : 'Create one, or start from a preset.'}
                    action={<Button variant="primary" size="sm" onClick={startNew}><Plus /> New topology</Button>}
                    className="rounded-xl border border-dashed border-border-strong"
                  />
                ) : (
                  <Grid>
                    {sections.mine.map((t) => (
                      <TopologyCard
                        key={t.id}
                        t={t}
                        onOpen={() => open(t.id)}
                        flags={ownFlags(t)}
                        primary={<Button size="sm" variant="secondary" onClick={() => open(t.id)}>Open</Button>}
                        menu={ownMenu(t)}
                      />
                    ))}
                  </Grid>
                )}
              </section>

              {sections.byStudent.length > 0 ? (
                <section>
                  <SectionTitle icon={<Users />}>Students</SectionTitle>
                  <div className="flex flex-col gap-5">
                    {sections.byStudent.map(([name, rows]) => (
                      <div key={name}>
                        <div className="mb-2 truncate text-xs font-medium text-fg">{name}</div>
                        <Grid>
                          {rows.map((t) => (
                            <TopologyCard
                              key={t.id}
                              t={t}
                              onOpen={() => open(t.id)}
                              marker={copyMarker(t)}
                              primary={<Button size="sm" variant="secondary" onClick={() => open(t.id)}>Open</Button>}
                              menu={<DropdownMenuItem variant="danger" onSelect={() => setDeleteTarget(t)}><Trash2 /> Delete</DropdownMenuItem>}
                            />
                          ))}
                        </Grid>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}
            </>
          )}

          {presets.length > 0 ? (
            <section>
              <SectionTitle icon={<LayoutTemplate />}>Presets</SectionTitle>
              <Grid>
                {presets.map((p) => (
                  <li key={p.id} className="flex flex-col gap-2 rounded-xl border border-border bg-surface p-4 shadow-sm">
                    <div className="text-sm font-medium">{p.name}</div>
                    <p className="line-clamp-3 text-xs text-fg-muted">{p.description}</p>
                    <div className="mt-auto flex items-center justify-between pt-1 text-2xs text-fg-subtle">
                      <span>{p.site_count} site{p.site_count === 1 ? '' : 's'} · {p.scenario_count} scenario{p.scenario_count === 1 ? '' : 's'}</span>
                      <Button size="sm" onClick={() => loadPreset(p.id)} loading={busyId === p.id} disabled={busyId !== null}>Use preset</Button>
                    </div>
                  </li>
                ))}
              </Grid>
            </section>
          ) : null}
        </div>
      </div>

      {canManageHost ? <LabsDialog open={labsOpen} onOpenChange={setLabsOpen} onChanged={() => void refresh()} /> : null}
      {canManageClass ? <ClassSheet open={classOpen} onOpenChange={setClassOpen} onChanged={() => void refresh()} /> : null}
      <ImagesSheet />

      <Dialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete topology"
        description={deleteTarget ? `“${deleteTarget.name}” will be removed permanently.` : undefined}
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="danger" onClick={() => void confirmDelete()}>Delete</Button>
          </>
        }
      >
        <p className="text-xs text-fg-muted">
          This cannot be undone. A deployed topology should be destroyed first.
          {deleteTarget?.published ? ' Students keep their copies.' : ''}
        </p>
      </Dialog>
    </div>
  );
}
