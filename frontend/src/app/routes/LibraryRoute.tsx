import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { Clock, FilePlus2, FolderOpen, LayoutTemplate, Plus, RefreshCw, Server, Trash2, Upload } from 'lucide-react';
import * as api from '@/api/client';
import { createNewTopology } from '@/features/deployment/actions';
import { Badge, Button, Dialog, EmptyState, IconButton, Spinner, toast } from '@/ui';
import { ThemeToggle } from '@/shell/ThemeToggle';
import { LabsDialog } from '@/features/system/LabsDialog';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

const STATUS_TONE: Record<string, 'success' | 'neutral' | 'warning' | 'danger'> = {
  deployed: 'success', idle: 'neutral', deploying: 'warning', destroying: 'warning', error: 'danger',
};

export function LibraryRoute() {
  const navigate = useNavigate();
  const [topologies, setTopologies] = useState<api.TopologySummary[] | null>(null);
  const [presets, setPresets] = useState<api.PresetSummary[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<api.TopologySummary | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [labsOpen, setLabsOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

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

  const open = (id: string) => void navigate(`/t/${encodeURIComponent(id)}`);

  const startNew = () => {
    createNewTopology();
    void navigate('/t/draft');
  };

  const loadPreset = async (id: string) => {
    setBusyId(id);
    try {
      const rec = await api.loadPreset(id);
      open(rec.id);
    } catch (err) {
      toast.error('Could not load preset', { description: api.errorMessage(err) });
    } finally {
      setBusyId(null);
    }
  };

  const importFile = async (file: File) => {
    setBusyId('import');
    try {
      const rec = await api.importJsonTopology(file);
      toast.success('Imported', { description: rec.name });
      open(rec.id);
    } catch (err) {
      toast.error('Import failed', { description: api.errorMessage(err) });
    } finally {
      setBusyId(null);
    }
  };

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

  return (
    <div className="flex h-full flex-col bg-app">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-surface px-4">
        <span className="text-sm font-semibold tracking-tight">AE3GIS</span>
        <span className="text-xs text-fg-muted">Topology library</span>
        <div className="ml-auto flex items-center gap-1">
          <Button size="sm" variant="ghost" onClick={() => setLabsOpen(true)}><Server /> Labs on this host</Button>
          <IconButton label="Refresh" size="icon-sm" onClick={() => { setTopologies(null); void refresh(); }}><RefreshCw /></IconButton>
          <ThemeToggle />
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
              onChange={(e) => { const f = e.target.files?.[0]; if (f) void importFile(f); e.target.value = ''; }}
            />
          </section>

          <section>
            <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-fg-muted"><FolderOpen className="size-3.5" /> Saved topologies</h2>
            {topologies === null ? (
              <div className="flex justify-center py-10"><Spinner /></div>
            ) : topologies.length === 0 ? (
              <EmptyState
                icon={<FilePlus2 />}
                title="No saved topologies"
                description="Create one from scratch or start from a preset below."
                action={<Button variant="primary" size="sm" onClick={startNew}><Plus /> New topology</Button>}
                className="rounded-xl border border-dashed border-border-strong"
              />
            ) : (
              <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {topologies.map((t) => (
                  <li key={t.id} className="group flex flex-col gap-2 rounded-xl border border-border bg-surface p-4 shadow-sm transition-colors hover:border-border-strong">
                    <div className="flex items-start justify-between gap-2">
                      <button type="button" onClick={() => open(t.id)} className="min-w-0 text-left">
                        <div className="truncate text-sm font-medium hover:text-accent">{t.name}</div>
                        <div className="mt-0.5 flex items-center gap-1 text-2xs text-fg-muted"><Clock className="size-3" /> {formatDate(t.updated_at)}</div>
                      </button>
                      <Badge tone={STATUS_TONE[t.status] ?? 'neutral'} dot={t.status === 'deployed' ? 'pulse' : true}>{t.status}</Badge>
                    </div>
                    <div className="mt-auto flex items-center gap-1 pt-1">
                      <Button size="sm" variant="secondary" onClick={() => open(t.id)}>Open</Button>
                      <IconButton label="Delete" size="icon-sm" className="ml-auto opacity-0 group-hover:opacity-100 hover:text-danger" onClick={() => setDeleteTarget(t)}><Trash2 /></IconButton>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {presets.length > 0 ? (
            <section>
              <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-fg-muted"><LayoutTemplate className="size-3.5" /> Presets</h2>
              <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {presets.map((p) => (
                  <li key={p.id} className="flex flex-col gap-2 rounded-xl border border-border bg-surface p-4 shadow-sm">
                    <div className="text-sm font-medium">{p.name}</div>
                    <p className="line-clamp-3 text-xs text-fg-muted">{p.description}</p>
                    <div className="mt-auto flex items-center justify-between pt-1 text-2xs text-fg-subtle">
                      <span>{p.site_count} site{p.site_count === 1 ? '' : 's'} · {p.scenario_count} scenario{p.scenario_count === 1 ? '' : 's'}</span>
                      <Button size="sm" onClick={() => void loadPreset(p.id)} loading={busyId === p.id} disabled={busyId !== null}>Use preset</Button>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      </div>

      <LabsDialog open={labsOpen} onOpenChange={setLabsOpen} onChanged={() => void refresh()} />

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
        <p className="text-xs text-fg-muted">This cannot be undone. A deployed topology should be destroyed first.</p>
      </Dialog>
    </div>
  );
}
