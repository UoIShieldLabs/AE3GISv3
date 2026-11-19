import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Activity, Boxes, Copy, EyeOff, FilePlus2, FolderOpen, GraduationCap, LayoutTemplate, Plus, RefreshCw, RotateCcw,
  SearchX, Server, Square, Trash2, Users,
} from 'lucide-react';
import * as api from '@/api/client';
import { createNewTopology } from '@/features/deployment/actions';
import {
  Button, Dialog, DropdownMenuItem, DropdownMenuSeparator, EmptyState, IconButton, Select, Spinner, Switch, Tooltip, toast,
} from '@/ui';
import { AppearanceMenu } from '@/shell/AppearanceMenu';
import { UserMenu } from '@/shell/UserMenu';
import { LabsDialog } from '@/features/system/LabsDialog';
import { ImagesSheet } from '@/features/images/ImagesSheet';
import { ClassDialogs } from '@/features/class/ClassDialogs';
import { ClassSettingsCard } from '@/features/class/ClassSettingsCard';
import { StudentHeader, StudentsTable } from '@/features/class/StudentsTable';
import { useClass } from '@/features/class/useClass';
import { LibraryRail } from '@/features/library/LibraryRail';
import { LibraryToolbar } from '@/features/library/LibraryToolbar';
import { NewTopologyMenu } from '@/features/library/NewTopologyMenu';
import { PresetsSection } from '@/features/library/PresetsSection';
import { Flag, type TopologyItem } from '@/features/library/TopologyCard';
import { TopologyCollection } from '@/features/library/TopologyCollection';
import {
  buildLibrary, holdsLab, lessonCopy, presetMatches, sectionCounts, sectionsFor, studentMatches, viewTopologies,
  type LibraryMode, type SectionId,
} from '@/features/library/model';
import { SECTION_ICON, sectionDescription, sectionLabel } from '@/features/library/sections';
import { useLibraryParams } from '@/features/library/useLibraryParams';
import { useCan, useIsStudent } from '@/lib/permissions';
import { useAppStore } from '@/store';

// Running labs and the class change while they are on screen.
const POLL_MS = 5000;
const EMPTY = 'rounded-xl border border-dashed border-border-strong';

/** Destroy from the library: a lab that is up, or a failed deploy that still holds one. */
const canDestroy = (t: api.TopologySummary) => t.status === 'deployed' || (t.status === 'error' && holdsLab(t));

function SectionHeader({ section, mode, aside }: { section: SectionId; mode: LibraryMode; aside?: React.ReactNode }) {
  const Icon = SECTION_ICON[section];
  const description = sectionDescription(section, mode);
  return (
    <div className="flex flex-wrap items-end gap-x-4 gap-y-1">
      <div className="min-w-0">
        <h1 className="flex items-center gap-2 text-base font-semibold [&>svg]:size-4 [&>svg]:text-fg-subtle"><Icon /> {sectionLabel(section, mode)}</h1>
        {description ? <p className="mt-0.5 text-xs text-fg-muted">{description}</p> : null}
      </div>
      {aside ? <div className="ml-auto text-xs text-fg-subtle">{aside}</div> : null}
    </div>
  );
}

export function LibraryRoute() {
  const navigate = useNavigate();
  const user = useAppStore((s) => s.user);
  const accounts = useAppStore((s) => !!s.authRequired);
  const isStudent = useIsStudent();
  const canPublish = useCan('publish') && accounts;
  const canManageClass = useCan('manageClass') && accounts;
  const canManageImages = useCan('manageImages');
  const canManageHost = useCan('manageHost');
  const layout = useAppStore((s) => s.libraryLayout);
  const sort = useAppStore((s) => s.librarySort);
  const mode: LibraryMode = !accounts ? 'open' : isStudent ? 'student' : 'instructor';
  const loc = useLibraryParams(mode);

  const [topologies, setTopologies] = useState<api.TopologySummary[] | null>(null);
  const [presets, setPresets] = useState<api.PresetSummary[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<api.TopologySummary | null>(null);
  // Unpublishing a lesson students started removes their copies: confirm first.
  const [unpublishTarget, setUnpublishTarget] = useState<api.TopologySummary | null>(null);
  // A student's "Start over" on a lesson they started: { lesson, their copy }.
  const [startOver, setStartOver] = useState<{ lesson: api.TopologySummary; copy: api.TopologySummary } | null>(null);
  const [destroyTarget, setDestroyTarget] = useState<api.TopologySummary | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [labsOpen, setLabsOpen] = useState(false);

  /** `quiet`: a poll, which keeps what is shown when it fails. */
  const refresh = useCallback(async (quiet = false) => {
    try {
      setTopologies(await api.listTopologies());
    } catch (err) {
      if (quiet) return;
      setTopologies((prev) => prev ?? []);
      toast.error('Could not load topologies', { description: api.errorMessage(err) });
    }
  }, []);
  const loadPresets = useCallback(async () => {
    setPresets((await api.listPresets().catch(() => ({ presets: [] }))).presets);
  }, []);

  useEffect(() => { void refresh(); void loadPresets(); }, [refresh, loadPresets]);

  const live = loc.section === 'running' || loc.section === 'students';
  useEffect(() => {
    if (!live) return;
    const timer = setInterval(() => void refresh(true), POLL_MS);
    return () => clearInterval(timer);
  }, [live, refresh]);

  const cls = useClass({
    enabled: canManageClass,
    polling: loc.section === 'students',
    onChanged: () => {
      void refresh();
      if (loc.student) loc.go('students'); // their page is gone
    },
  });

  const lib = useMemo(
    () => buildLibrary({ topologies: topologies ?? [], students: cls.students?.students ?? null, userId: user?.id, mode }),
    [topologies, cls.students, user?.id, mode],
  );
  const counts = useMemo(() => sectionCounts(lib, presets, loc.q), [lib, presets, loc.q]);

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

  /** Students who started a lesson (the instructor sees their copies). */
  const startedBy = (lessonId: string) => lib.lessonStats.get(lessonId)?.started ?? 0;

  const setPublished = (t: api.TopologySummary, published: boolean) =>
    void withBusy(t.id, async () => {
      const rec = await api.setPublished(t.id, published);
      toast.success(published ? 'Published to students' : 'No longer published', { description: t.name });
      if (published) {
        setTopologies((prev) => prev?.map((x) => (x.id === t.id ? { ...x, published: rec.published ?? published } : x)) ?? null);
      } else {
        await refresh(); // the students' copies are gone
      }
    }, 'Could not change publishing');

  const togglePublished = (t: api.TopologySummary, published: boolean) => {
    if (!published && startedBy(t.id) > 0) setUnpublishTarget(t);
    else setPublished(t, published);
  };

  /** Into "My topologies": the student's work if they started, else the lesson. */
  const duplicateLesson = (lesson: api.TopologySummary) =>
    void withBusy(lesson.id, async () => {
      const started = lib.copies.get(lesson.id);
      const rec = started ? await api.copyTopology(started.id) : await api.copyTopology(lesson.id, { duplicate: true });
      toast.success('Duplicated to My topologies', { description: rec.name, action: { label: 'Open', onClick: () => open(rec.id) } });
      await refresh();
    }, 'Could not duplicate');

  const confirmStartOver = () => {
    if (!startOver) return;
    const { lesson, copy } = startOver;
    setStartOver(null);
    void withBusy(lesson.id, async () => {
      await api.resetTopology(copy.id);
      toast.success('Started over', { description: lesson.name });
      await refresh();
    }, 'Could not start over');
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteTopology(deleteTarget.id);
      toast.success('Deleted', { description: deleteTarget.name });
      await refresh(); // a lesson takes its students' copies with it
    } catch (err) {
      toast.error('Delete failed', { description: api.errorMessage(err) });
    }
    setDeleteTarget(null);
  };

  const confirmDestroy = (save: boolean) => {
    const t = destroyTarget;
    if (!t) return;
    setDestroyTarget(null);
    void withBusy(t.id, async () => {
      await api.destroyTopology(t.id, { save });
      toast.success(save ? 'Saving and destroying the lab' : 'Destroying the lab', { description: t.name });
      await refresh();
      if (canManageClass) void cls.refresh();
    }, 'Could not destroy the lab');
  };

  // ── What a card / row shows, per section ──────────────────────────────

  const openButton = (onClick: () => void) => <Button size="sm" variant="secondary" onClick={onClick}>Open</Button>;

  const destroyMenuItem = (t: api.TopologySummary) =>
    canDestroy(t) ? <DropdownMenuItem onSelect={() => setDestroyTarget(t)}><Square /> Destroy lab…</DropdownMenuItem> : null;

  const publishSwitch = (t: api.TopologySummary) =>
    canPublish ? (
      <label className="mr-1 flex cursor-pointer items-center gap-1.5 text-2xs text-fg-muted" title={t.published ? 'Students see it as a lesson' : 'Publish to students as a lesson'}>
        Publish
        <Switch checked={!!t.published} disabled={busyId === t.id} onCheckedChange={(v) => togglePublished(t, v)} aria-label={`Publish ${t.name}`} />
      </label>
    ) : null;

  const ownFlags = (t: api.TopologySummary) => (
    <>
      {canPublish && t.published ? <Flag tone="accent" title="Students see it and open their own copy">Published</Flag> : null}
      {t.update_available ? <Flag tone="warning" title="Your instructor changed it since your copy was made">Updated</Flag> : null}
    </>
  );

  /** For the instructor: which lesson a student's topology was copied from. */
  const copyMarker = (t: api.TopologySummary) => {
    if (!t.source_id) return undefined;
    const from = lib.names.get(t.source_id);
    return (
      <Tooltip content={from ? `Copy of “${from}”` : 'Copy of a published topology'}>
        <span className="flex shrink-0 text-fg-subtle"><GraduationCap className="size-3.5" /></span>
      </Tooltip>
    );
  };

  const ownItem = (t: api.TopologySummary, { publish = true } = {}): TopologyItem => ({
    t,
    onOpen: () => open(t.id),
    flags: ownFlags(t),
    primary: openButton(() => open(t.id)),
    trailing: publish ? publishSwitch(t) : undefined,
    menu: (
      <>
        <DropdownMenuItem onSelect={() => duplicate(t)}><Copy /> Duplicate</DropdownMenuItem>
        {destroyMenuItem(t)}
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="danger" onSelect={() => setDeleteTarget(t)}><Trash2 /> Delete</DropdownMenuItem>
      </>
    ),
  });

  /** The instructor's view of a student's topology. */
  const studentItem = (t: api.TopologySummary): TopologyItem => ({
    t,
    onOpen: () => open(t.id),
    marker: copyMarker(t),
    primary: openButton(() => open(t.id)),
    menu: (
      <>
        {canDestroy(t) ? <>{destroyMenuItem(t)}<DropdownMenuSeparator /></> : null}
        <DropdownMenuItem variant="danger" onSelect={() => setDeleteTarget(t)}><Trash2 /> Delete</DropdownMenuItem>
      </>
    ),
  });

  const runningItem = (t: api.TopologySummary): TopologyItem =>
    t.owner ? { ...studentItem(t), owner: t.owner.username } : ownItem(t, { publish: false });

  /** The instructor's published topology: who started it, stop publishing. */
  const lessonItem = (t: api.TopologySummary): TopologyItem => {
    const stats = lib.lessonStats.get(t.id) ?? { started: 0, running: 0 };
    return {
      t,
      onOpen: () => open(t.id),
      primary: openButton(() => open(t.id)),
      trailing: canManageClass ? (
        <Button size="xs" variant="ghost" onClick={() => loc.go('students', { lesson: t.id })} title="See who started it">
          <Users /> {stats.started} started{stats.running ? ` · ${stats.running} running` : ''}
        </Button>
      ) : undefined,
      menu: (
        <>
          <DropdownMenuItem onSelect={() => duplicate(t)}><Copy /> Duplicate</DropdownMenuItem>
          {destroyMenuItem(t)}
          <DropdownMenuItem onSelect={() => togglePublished(t, false)}><EyeOff /> Stop publishing</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="danger" onSelect={() => setDeleteTarget(t)}><Trash2 /> Delete</DropdownMenuItem>
        </>
      ),
    };
  };

  /** A student's lesson: opens (or starts) their copy, shows its status. */
  const studentLessonItem = (t: api.TopologySummary): TopologyItem => {
    const mineCopy = lib.copies.get(t.id);
    return {
      t,
      status: mineCopy?.status ?? 'idle',
      onOpen: () => openCopy(t),
      flags: mineCopy?.update_available ? <Flag tone="warning" title="Changed since you started; reset it from the editor">Updated</Flag> : null,
      primary: <Button size="sm" variant="secondary" onClick={() => openCopy(t)} loading={busyId === t.id} disabled={busyId !== null}>Open</Button>,
      menu: (
        <>
          <DropdownMenuItem onSelect={() => duplicateLesson(t)}><Copy /> Duplicate to My topologies</DropdownMenuItem>
          {mineCopy ? <DropdownMenuItem onSelect={() => setStartOver({ lesson: t, copy: mineCopy })}><RotateCcw /> Start over</DropdownMenuItem> : null}
        </>
      ),
    };
  };

  // ── Sections ──────────────────────────────────────────────────────────

  const noMatches = (
    <EmptyState
      icon={<SearchX />}
      title="Nothing matches"
      description={loc.runningOnly ? 'Try another search, or show what is not running too.' : 'Try another search.'}
      action={<Button size="sm" onClick={loc.clearFilters}>Clear filters</Button>}
      className={EMPTY}
    />
  );

  const toolbar = ({ runningFilter = true, placeholder }: { runningFilter?: boolean; placeholder?: string } = {}) => (
    <LibraryToolbar
      q={loc.q}
      onQuery={loc.setQuery}
      placeholder={placeholder}
      runningOnly={loc.runningOnly}
      onRunningOnly={runningFilter ? loc.setRunningOnly : undefined}
      sort={sort}
      onSort={useAppStore.getState().setLibrarySort}
      layout={layout}
      onLayout={useAppStore.getState().setLibraryLayout}
    />
  );

  const collection = (
    items: api.TopologySummary[],
    toItem: (t: api.TopologySummary) => TopologyItem,
    { empty, statusOf, labOf, showOwner, runningFilter = true }: {
      empty: React.ReactNode;
      statusOf?: (t: api.TopologySummary) => string;
      labOf?: (t: api.TopologySummary) => api.TopologySummary | undefined;
      showOwner?: boolean;
      runningFilter?: boolean;
    },
  ) => {
    if (items.length === 0) return empty;
    const shown = viewTopologies(items, { q: loc.q, sort, runningOnly: runningFilter && loc.runningOnly, statusOf, labOf });
    return <TopologyCollection items={shown.map(toItem)} layout={layout} showOwner={showOwner} empty={noMatches} />;
  };

  const newTopologyAction = <Button variant="primary" size="sm" onClick={startNew}><Plus /> New topology</Button>;

  function studentsSection() {
    if (loc.student) {
      const row = lib.students.find((s) => s.id === loc.student);
      if (!row) {
        return cls.students === null
          ? <div className="flex justify-center py-10"><Spinner /></div>
          : <EmptyState icon={<Users />} title="Not in the class" description="This student was removed." action={<Button size="sm" onClick={() => loc.go('students')}>All students</Button>} className={EMPTY} />;
      }
      return (
        <>
          <StudentHeader row={row} cls={cls} onBack={() => loc.go('students')} />
          {toolbar()}
          {collection(row.topologies, studentItem, {
            empty: <EmptyState icon={<FolderOpen />} title="No topologies yet" description={`${row.username} has not started a lesson or made a topology.`} className={EMPTY} />,
          })}
        </>
      );
    }
    const lesson = loc.lesson ? lib.lessons.find((t) => t.id === loc.lesson) ?? null : null;
    const rows = lib.students.filter((s) => studentMatches(s, loc.q));
    const runningStudents = lib.students.filter((s) => s.running.length > 0).length;
    const maxLabs = cls.students?.max_labs ?? 0;
    const started = lesson ? lib.students.filter((s) => lessonCopy(s, lesson.id)).length : 0;
    const lessonRunning = lesson ? lib.lessonStats.get(lesson.id)?.running ?? 0 : 0;
    return (
      <>
        <SectionHeader
          section="students"
          mode={mode}
          aside={`${lib.students.length} student${lib.students.length === 1 ? '' : 's'} · ${runningStudents} running · ${maxLabs > 0 ? `max ${maxLabs} lab${maxLabs === 1 ? '' : 's'} each` : 'no lab limit'}`}
        />
        <ClassSettingsCard cls={cls} />
        <LibraryToolbar q={loc.q} onQuery={loc.setQuery} placeholder="Search students">
          {lib.lessons.length > 0 ? (
            <Select
              size="sm"
              aria-label="Follow a lesson"
              value={lesson?.id ?? 'all'}
              onValueChange={(v) => loc.setLesson(v === 'all' ? null : v)}
              options={[{ value: 'all', label: 'All students' }, ...lib.lessons.map((t) => ({ value: t.id, label: t.name, group: 'Who started a lesson' }))]}
              className="w-auto max-w-80 min-w-44"
            />
          ) : null}
          {lesson ? <span className="text-xs text-fg-muted">{started} of {lib.students.length} started · {lessonRunning} running</span> : null}
        </LibraryToolbar>
        {lib.students.length === 0 ? (
          cls.students === null
            ? <div className="flex justify-center py-10"><Spinner /></div>
            : <EmptyState icon={<Users />} title="No students yet" description="Turn on sign-up and share the join code." className={EMPTY} />
        ) : rows.length === 0 ? noMatches : (
          <StudentsTable rows={rows} lesson={lesson} onOpen={(id) => loc.go('students', { student: id })} cls={cls} />
        )}
      </>
    );
  }

  function section() {
    switch (loc.section) {
      case 'running':
        return (
          <>
            <SectionHeader section="running" mode={mode} />
            {toolbar({ runningFilter: false })}
            {collection(lib.running, runningItem, {
              showOwner: mode === 'instructor',
              runningFilter: false,
              empty: <EmptyState icon={<Activity />} title="Nothing running" description="Deployed labs show up here." className={EMPTY} />,
            })}
          </>
        );
      case 'mine':
        return (
          <>
            <SectionHeader section="mine" mode={mode} />
            {toolbar()}
            {collection(lib.mine, (t) => ownItem(t), {
              empty: (
                <EmptyState
                  icon={<FilePlus2 />}
                  title="No saved topologies"
                  description={mode === 'student' ? 'Create one, or start a lesson.' : 'Create one, or start from a preset.'}
                  action={newTopologyAction}
                  className={EMPTY}
                />
              ),
            })}
          </>
        );
      case 'lessons':
        return (
          <>
            <SectionHeader section="lessons" mode={mode} />
            {toolbar()}
            {mode === 'student'
              ? collection(lib.lessons, studentLessonItem, {
                statusOf: (t) => lib.copies.get(t.id)?.status ?? 'idle',
                labOf: (t) => lib.copies.get(t.id),
                empty: <EmptyState icon={<GraduationCap />} title="No lessons yet" description="Your instructor’s lessons show up here." className={EMPTY} />,
              })
              : collection(lib.lessons, lessonItem, {
                empty: (
                  <EmptyState
                    icon={<GraduationCap />}
                    title="Nothing published"
                    description="Turn on Publish on one of your topologies to give it to your students."
                    action={<Button size="sm" onClick={() => loc.go('mine')}>My topologies</Button>}
                    className={EMPTY}
                  />
                ),
              })}
          </>
        );
      case 'students':
        return studentsSection();
      case 'presets': {
        const shown = presets.filter((p) => presetMatches(p, loc.q));
        return (
          <>
            <SectionHeader section="presets" mode={mode} />
            <LibraryToolbar q={loc.q} onQuery={loc.setQuery} placeholder="Search presets" />
            <PresetsSection
              presets={shown}
              busyId={busyId}
              onUse={loadPreset}
              empty={presets.length ? noMatches : <EmptyState icon={<LayoutTemplate />} title="No presets" description="Preset files live in backend/presets." className={EMPTY} />}
            />
          </>
        );
      }
    }
  }

  return (
    <div className="flex h-full flex-col bg-app">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-surface px-4">
        <span className="ae-brand text-sm font-semibold tracking-tight">AE3GIS</span>
        <span className="hidden text-xs text-fg-muted sm:inline">Topology library</span>
        <div className="ml-auto flex items-center gap-1">
          {canManageImages ? <Button size="sm" variant="ghost" onClick={() => useAppStore.getState().openImages()}><Boxes /> Images</Button> : null}
          {canManageHost ? <Button size="sm" variant="ghost" onClick={() => setLabsOpen(true)}><Server /> Labs on this host</Button> : null}
          <IconButton
            label="Refresh"
            size="icon-sm"
            onClick={() => { setTopologies(null); void refresh(); void loadPresets(); if (canManageClass) void cls.refresh(); }}
          >
            <RefreshCw />
          </IconButton>
          <AppearanceMenu />
          <UserMenu />
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <aside className="flex shrink-0 items-center gap-2 border-b border-border bg-surface-2/40 p-2 md:w-60 md:flex-col md:items-stretch md:gap-3 md:overflow-y-auto md:border-r md:border-b-0 md:p-3">
          <NewTopologyMenu
            presets={presets}
            busy={busyId === 'import' || presets.some((p) => p.id === busyId)}
            onBlank={startNew}
            onPreset={loadPreset}
            onImport={importFile}
            onBrowsePresets={() => loc.go('presets')}
          />
          <LibraryRail
            mode={mode}
            sections={sectionsFor(mode)}
            counts={topologies === null ? null : counts}
            current={loc.section}
            student={loc.student}
            students={lib.students}
            q={loc.q}
            onGo={loc.go}
          />
        </aside>

        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">
          {/* Fills the space beside the rail; centred past 1600px so a very
              wide screen does not stretch rows into long lines. */}
          <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-4 p-4 md:p-6 xl:px-8">
            {topologies === null && loc.section !== 'presets' ? <div className="flex justify-center py-10"><Spinner /></div> : section()}
          </div>
        </main>
      </div>

      {canManageHost ? <LabsDialog open={labsOpen} onOpenChange={setLabsOpen} onChanged={() => void refresh()} /> : null}
      {canManageClass ? <ClassDialogs cls={cls} /> : null}
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
          {deleteTarget && startedBy(deleteTarget.id) > 0 ? ` ${studentsText(startedBy(deleteTarget.id))}` : ''}
        </p>
      </Dialog>

      <Dialog
        open={!!unpublishTarget}
        onOpenChange={(o) => !o && setUnpublishTarget(null)}
        title="Stop publishing?"
        description={unpublishTarget ? `“${unpublishTarget.name}”` : undefined}
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setUnpublishTarget(null)}>Cancel</Button>
            <Button variant="danger" onClick={() => { const t = unpublishTarget; setUnpublishTarget(null); if (t) setPublished(t, false); }}>Stop publishing</Button>
          </>
        }
      >
        <p className="text-xs text-fg-muted">{unpublishTarget ? studentsText(startedBy(unpublishTarget.id)) : null}</p>
      </Dialog>

      <Dialog
        open={!!startOver}
        onOpenChange={(o) => !o && setStartOver(null)}
        title="Start over?"
        description={startOver ? `“${startOver.lesson.name}”` : undefined}
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setStartOver(null)}>Cancel</Button>
            <Button variant="danger" onClick={confirmStartOver}>Start over</Button>
          </>
        }
      >
        <p className="text-xs text-fg-muted">Your changes and saved lab state are discarded, and you get the latest version. Duplicate it first to keep your work.</p>
      </Dialog>

      <Dialog
        open={!!destroyTarget}
        onOpenChange={(o) => !o && setDestroyTarget(null)}
        title="Destroy this lab?"
        description={destroyTarget ? (destroyTarget.owner ? `${destroyTarget.owner.username}’s “${destroyTarget.name}”` : `“${destroyTarget.name}”`) : undefined}
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDestroyTarget(null)}>Cancel</Button>
            <Button variant="secondary" onClick={() => confirmDestroy(true)}>Save &amp; destroy</Button>
            <Button variant="danger" onClick={() => confirmDestroy(false)}>Destroy</Button>
          </>
        }
      >
        <p className="text-xs text-fg-muted">Save &amp; destroy keeps the lab’s state, so the next deploy resumes it.</p>
      </Dialog>
    </div>
  );
}

/** What unpublishing or deleting a lesson does to the students who started it. */
function studentsText(n: number): string {
  return `${n} student${n === 1 ? '' : 's'} started this lesson. Their copies and any running labs are removed; anything they duplicated stays.`;
}
