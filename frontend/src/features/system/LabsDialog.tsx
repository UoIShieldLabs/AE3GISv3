import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Trash2, Wrench } from 'lucide-react';
import * as api from '@/api/client';
import { Badge, Button, Dialog, IconButton, Spinner, toast } from '@/ui';

export interface LabsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called after a purge or reconcile so the library can refresh statuses. */
  onChanged?: () => void;
}

/** Every lab the engine is running on this host, matched against saved topologies. */
export function LabsDialog({ open, onOpenChange, onChanged }: LabsDialogProps) {
  const [report, setReport] = useState<api.LabsReport | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setReport(await api.listLabs());
    } catch (err) {
      toast.error('Could not list labs', { description: api.errorMessage(err) });
      setReport({ labs: [], stale: [] });
    }
  }, []);

  useEffect(() => { if (open) { setReport(null); void refresh(); } }, [open, refresh]);

  const purge = async (hash: string) => {
    setBusy(hash);
    try {
      await api.purgeLab(hash);
      toast.success('Lab purged');
      await refresh();
      onChanged?.();
    } catch (err) {
      toast.error('Purge failed', { description: api.errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };

  const reconcile = async () => {
    setBusy('reconcile');
    try {
      const r = await api.reconcileLabs();
      toast.success('Reconciled', { description: `${r.reset} topolog${r.reset === 1 ? 'y' : 'ies'} reset, ${r.orphans} orphan lab${r.orphans === 1 ? '' : 's'} left` });
      await refresh();
      onChanged?.();
    } catch (err) {
      toast.error('Reconcile failed', { description: api.errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Labs on this host"
      description="What the deployment engine is actually running, matched against saved topologies."
      size="lg"
      footer={
        <>
          <IconButton label="Refresh" size="icon-sm" onClick={() => void refresh()}><RefreshCw /></IconButton>
          <Button variant="secondary" onClick={() => void reconcile()} loading={busy === 'reconcile'}><Wrench /> Reconcile</Button>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Close</Button>
        </>
      }
    >
      {report === null ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : (
        <div className="flex flex-col gap-4 text-xs">
          {report.labs.length === 0 ? <p className="text-fg-muted">No labs are running.</p> : (
            <table className="w-full">
              <thead className="text-left text-2xs uppercase tracking-wide text-fg-subtle">
                <tr><th className="pb-1 font-medium">Lab</th><th className="pb-1 font-medium">Topology</th><th className="pb-1 font-medium">Machines</th><th className="pb-1 text-right font-medium">Running</th><th /></tr>
              </thead>
              <tbody>
                {report.labs.map((lab) => (
                  <tr key={lab.lab_hash} className="border-t border-border align-top">
                    <td className="py-2 pr-2">
                      <Badge tone={lab.classification === 'tracked' ? 'success' : 'warning'}>{lab.classification}</Badge>
                      <div className="mt-1 font-mono text-2xs text-fg-subtle">{lab.lab_hash}</div>
                    </td>
                    <td className="py-2 pr-2">{lab.topology_name ?? <span className="text-fg-subtle">—</span>}</td>
                    <td className="py-2 pr-2 font-mono text-2xs text-fg-muted">{lab.machines.join(', ')}</td>
                    <td className="py-2 text-right tabular">{lab.running}/{lab.total}</td>
                    <td className="py-2 pl-2 text-right">
                      <Button size="xs" variant="danger-soft" onClick={() => void purge(lab.lab_hash)} loading={busy === lab.lab_hash} disabled={busy !== null}><Trash2 /> Purge</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {report.stale.length > 0 ? (
            <div className="rounded-md bg-warning-soft p-3">
              <div className="mb-1 font-medium text-warning">Marked deployed but no lab found</div>
              <ul className="list-disc pl-4 text-fg-muted">
                {report.stale.map((s) => <li key={s.topology_id}>{s.topology_name} <span className="font-mono text-2xs">{s.lab_hash}</span></li>)}
              </ul>
              <p className="mt-1 text-2xs text-fg-muted">Reconcile resets them to idle.</p>
            </div>
          ) : null}
          <p className="text-2xs text-fg-subtle">Orphans are labs no saved topology references, usually left behind by an earlier backend instance. Purging removes their containers and networks.</p>
        </div>
      )}
    </Dialog>
  );
}
