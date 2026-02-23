import { useEffect, useState } from 'react';
import { Dialog } from './ui/Dialog';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
import { ImportClabDialog } from './dialogs/ImportClabDialog';
import { listTopologies, deleteTopology, type TopologySummary } from '../api/client';
import './TopologyBrowser.css';

interface TopologyBrowserProps {
  open: boolean;
  onClose: () => void;
  onLoad: (id: string) => void;
  currentId: string | null;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function TopologyBrowser({ open, onClose, onLoad, currentId }: TopologyBrowserProps) {
  const [topologies, setTopologies] = useState<TopologySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TopologySummary | null>(null);
  const [importOpen, setImportOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    void listTopologies()
      .then((topos) => { setLoading(false); setTopologies(topos); })
      .catch(() => { setLoading(false); setTopologies([]); });
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
  }, [open]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteTopology(deleteTarget.id);
      setTopologies((prev) => prev.filter((t) => t.id !== deleteTarget.id));
    } catch {
      // silently handle — could add error toast later
    }
    setDeleteTarget(null);
  };

  const handleLoad = (id: string) => {
    onLoad(id);
    onClose();
  };

  const handleImported = (topo: TopologySummary) => {
    setTopologies((prev) => [topo, ...prev]);
    setImportOpen(false);
  };

  return (
    <>
      <Dialog title="Load Topology" open={open} onClose={onClose} width={520}>
        <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={() => setImportOpen(true)}
            style={{
              padding: '5px 12px',
              background: 'rgba(0, 212, 255, 0.06)',
              border: '1px solid rgba(0, 212, 255, 0.4)',
              borderRadius: '4px',
              color: 'var(--neon-cyan)',
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              cursor: 'pointer',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Import .clab
          </button>
        </div>

        {loading ? (
          <div className="topology-browser-loading">Loading...</div>
        ) : topologies.length === 0 ? (
          <div className="topology-browser-empty">No saved topologies</div>
        ) : (
          <div className="topology-browser-list">
            {topologies.map((topo) => (
              <div
                key={topo.id}
                className={`topology-browser-row${topo.id === currentId ? ' current' : ''}`}
              >
                <div className="topology-browser-info">
                  <div className="topology-browser-name">{topo.name}</div>
                  <div className="topology-browser-meta">
                    Updated {formatDate(topo.updated_at)}
                  </div>
                </div>

                <span className={`topology-browser-badge badge-${topo.status}`}>
                  {topo.status}
                </span>

                <div className="topology-browser-actions">
                  <button className="btn-load" onClick={() => handleLoad(topo.id)}>
                    Load
                  </button>
                  <button className="btn-delete" onClick={() => setDeleteTarget(topo)}>
                    Del
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Topology"
        message={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      <ImportClabDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={handleImported}
      />
    </>
  );
}
