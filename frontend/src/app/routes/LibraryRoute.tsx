import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Boxes, Clock, Copy, FilePlus2, FolderOpen, GraduationCap, LayoutTemplate, Plus, RefreshCw, Send, Server, Trash2, Upload, Users,
} from 'lucide-react';
import * as api from '@/api/client';
import { createNewTopology } from '@/features/deployment/actions';
import { Badge, Button, Dialog, EmptyState, IconButton, Spinner, Switch, Tooltip, toast } from '@/ui';
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

/** One topology: name, when, status; `badges` and `actions` vary by section. */
function TopologyCard({ t, onOpen, badges, actions }: {
  t: api.TopologySummary;
  onOpen: () => void;
  badges?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <li className="group flex flex-col gap-2 rounded-xl border border-border bg-surface p-4 shadow-sm transition-colors hover:border-border-strong">
      <div className="flex items-start justify-between gap-2">
        <button type="button" onClick={onOpen} className="min-w-0 text-left">
          <div className="truncate text-sm font-medium hover:text-accent">{t.name}</div>
          <div className="mt-0.5 flex items-center gap-1 text-2xs text-fg-muted"><Clock className="size-3" /> {formatDate(t.updated_at)}</div>
        </button>
        <Badge tone={STATUS_TONE[t.status] ?? 'neutral'} dot={t.status === 'deployed' ? 'pulse' : true}>{t.status}</Badge>
      </div>
      {badges ? <div className="flex flex-wrap items-center gap-1">{badges}</div> : null}
      <div className="mt-auto flex items-center gap-1 pt-1">{actions}</div>
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
    const mine = all.filter((t) => (isStudent ? t.owner?.id === user?.id : !t.owner));
    const published = isStudent ? all.filter((t) => t.published && t.owner?.id !== user?.id) : [];
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

  const ownActions = (t: api.TopologySummary) => (
    <>
      <Button size="sm" variant="secondary" onClick={() => open(t.id)}>Open</Button>
      <IconButton label="Duplicate" size="icon-sm" className="opacity-0 group-hover:opacity-100" onClick={() => duplicate(t)} disabled={busyId !== null}><Copy /></IconButton>
      {canPublish ? (
        <Tooltip content={t.published ? 'Students see it and open their own copy' : 'Publish to students'}>
          <label className="ml-auto flex cursor-pointer items-center gap-1.5 text-2xs text-fg-muted">
            <Send className="size-3" /> Publish
            <Switch checked={!!t.published} disabled={busyId === t.id} onCheckedChange={(v) => togglePublished(t, v)} aria-label={`Publish ${t.name}`} />
          </label>
        </Tooltip>
      ) : null}
      <IconButton label="Delete" size="icon-sm" className={`${canPublish ? '' : 'ml-auto '}opacity-0 group-hover:opacity-100 hover:text-danger`} onClick={() => setDeleteTarget(t)}><Trash2 /></IconButton>
    </>
  );

  const ownBadges = (t: api.TopologySummary) => {
    const badges: React.ReactNode[] = [];
    if (t.published && !isStudent) badges.push(<Badge key="pub" tone="accent"><Send className="size-2.5" /> Published</Badge>);
    if (t.source_id) {
      const from = sections.names.get(t.source_id);
      badges.push(<Badge key="src" tone="outline"><GraduationCap className="size-2.5" /> {from ? `from “${from}”` : 'from your instructor'}</Badge>);
    }
    if (t.update_available) badges.push(<Badge key="upd" tone="warning">Update available</Badge>);
    return badges.length ? badges : undefined;
  };

  const copyOf = (sourceId: string) => sections.mine.find((t) => t.source_id === sourceId);

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
                  <SectionTitle icon={<GraduationCap />}>From your instructor</SectionTitle>
                  {sections.published.length === 0 ? (
                    <p className="rounded-xl border border-dashed border-border-strong p-4 text-xs text-fg-muted">Nothing published yet. Labs your instructor publishes appear here.</p>
                  ) : (
                    <Grid>
                      {sections.published.map((t) => {
                        const mineCopy = copyOf(t.id);
                        return (
                          <TopologyCard
                            key={t.id}
                            t={{ ...t, status: mineCopy?.status ?? 'idle' }}
                            onOpen={() => openCopy(t)}
                            badges={mineCopy?.update_available ? <Badge tone="warning">Update available</Badge> : undefined}
                            actions={
                              <Button size="sm" variant={mineCopy ? 'secondary' : 'primary'} onClick={() => openCopy(t)} loading={busyId === t.id} disabled={busyId !== null}>
                                {mineCopy ? 'Open my copy' : 'Start'}
                              </Button>
                            }
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
                    description={isStudent ? 'Start one your instructor published, create your own, or start from a preset below.' : 'Create one from scratch or start from a preset below.'}
                    action={<Button variant="primary" size="sm" onClick={startNew}><Plus /> New topology</Button>}
                    className="rounded-xl border border-dashed border-border-strong"
                  />
                ) : (
                  <Grid>
                    {sections.mine.map((t) => (
                      <TopologyCard key={t.id} t={t} onOpen={() => open(t.id)} badges={ownBadges(t)} actions={ownActions(t)} />
                    ))}
                  </Grid>
                )}
              </section>

              {sections.byStudent.length > 0 ? (
                <section>
                  <SectionTitle icon={<Users />} aside={`${sections.byStudent.length} student${sections.byStudent.length === 1 ? '' : 's'}`}>Students' topologies</SectionTitle>
                  <div className="flex flex-col gap-5">
                    {sections.byStudent.map(([name, rows]) => (
                      <div key={name}>
                        <div className="mb-2 text-xs font-medium text-fg">{name}</div>
                        <Grid>
                          {rows.map((t) => (
                            <TopologyCard
                              key={t.id}
                              t={t}
                              onOpen={() => open(t.id)}
                              badges={ownBadges(t)}
                              actions={
                                <>
                                  <Button size="sm" variant="secondary" onClick={() => open(t.id)}>Open</Button>
                                  <IconButton label="Delete" size="icon-sm" className="ml-auto opacity-0 group-hover:opacity-100 hover:text-danger" onClick={() => setDeleteTarget(t)}><Trash2 /></IconButton>
                                </>
                              }
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
          {deleteTarget?.published ? ' Students keep the copies they made.' : ''}
        </p>
      </Dialog>
    </div>
  );
}
