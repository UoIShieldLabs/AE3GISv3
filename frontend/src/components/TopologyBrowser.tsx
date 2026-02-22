import { useEffect, useState } from 'react';
import { Dialog } from './ui/Dialog';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
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

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    listTopologies()
      .then(setTopologies)
      .catch(() => setTopologies([]))
      .finally(() => setLoading(false));
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

  return (
    <>
      <Dialog title="Load Topology" open={open} onClose={onClose} width={520}>
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
    </>
  );
}
