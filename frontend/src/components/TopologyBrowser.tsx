import { useEffect, useState } from 'react';
import { Dialog } from './ui/Dialog';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
import { ImportClabDialog } from './dialogs/ImportClabDialog';
import { ImportJsonDialog } from './dialogs/ImportJsonDialog';
import { listTopologies, deleteTopology, listPresets, loadPreset, type TopologySummary, type PresetSummary } from '../api/client';
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
  const [importJsonOpen, setImportJsonOpen] = useState(false);

  // Presets
  const [presets, setPresets] = useState<PresetSummary[]>([]);
  const [presetsOpen, setPresetsOpen] = useState(false);
  const [loadingPreset, setLoadingPreset] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    void listTopologies()
      .then((topos) => { setLoading(false); setTopologies(topos); })
      .catch(() => { setLoading(false); setTopologies([]); });
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    listPresets()
      .then(res => setPresets(res.presets))
      .catch(() => setPresets([]));
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
    setImportJsonOpen(false);
  };

  const handleLoadPreset = async (presetId: string) => {
    setLoadingPreset(presetId);
    try {
      const result = await loadPreset(presetId);
      onLoad(result.id);
      onClose();
    } catch (err) {
      console.error('Failed to load preset:', err);
    } finally {
      setLoadingPreset(null);
    }
  };

  return (
    <>
      <Dialog title="Load Topology" open={open} onClose={onClose} width={520}>
        <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button
            onClick={() => setImportJsonOpen(true)}
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
            Import JSON
          </button>
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

        {/* Preset templates */}
        {presets.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <button
              onClick={() => setPresetsOpen(!presetsOpen)}
              style={{
                width: '100%',
                padding: '10px 14px',
                background: 'rgba(255, 170, 0, 0.05)',
                border: '1px solid rgba(255, 170, 0, 0.3)',
                borderRadius: '4px',
                color: '#ffaa00',
                fontFamily: 'var(--font-mono)',
                fontSize: '13px',
                cursor: 'pointer',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                textAlign: 'left',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span>Preset Templates ({presets.length})</span>
              <span style={{ fontSize: '10px' }}>{presetsOpen ? '▲' : '▼'}</span>
            </button>
            {presetsOpen && (
              <div style={{
                border: '1px solid rgba(255, 170, 0, 0.15)',
                borderTop: 'none',
                borderRadius: '0 0 4px 4px',
                overflow: 'hidden',
              }}>
                {presets.map(preset => (
                  <div key={preset.id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 14px',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                    background: 'rgba(20, 20, 30, 0.5)',
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '14px',
                        color: 'var(--text-primary)',
                        marginBottom: '2px',
                      }}>
                        {preset.name}
                      </div>
                      <div style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        color: 'var(--text-dim)',
                      }}>
                        {preset.site_count} site{preset.site_count !== 1 ? 's' : ''} · {preset.scenario_count} scenario{preset.scenario_count !== 1 ? 's' : ''}
                        {preset.description && ` — ${preset.description.slice(0, 80)}${preset.description.length > 80 ? '…' : ''}`}
                      </div>
                    </div>
                    <button
                      onClick={() => handleLoadPreset(preset.id)}
                      disabled={loadingPreset !== null}
                      style={{
                        padding: '6px 14px',
                        background: 'rgba(255, 170, 0, 0.08)',
                        border: '1px solid #ffaa00',
                        color: '#ffaa00',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '12px',
                        textTransform: 'uppercase',
                        letterSpacing: '1px',
                        borderRadius: '4px',
                        cursor: loadingPreset ? 'not-allowed' : 'pointer',
                        whiteSpace: 'nowrap',
                        opacity: loadingPreset === preset.id ? 0.6 : 1,
                      }}
                    >
                      {loadingPreset === preset.id ? 'Loading...' : 'Load'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

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

      <ImportJsonDialog
        open={importJsonOpen}
        onClose={() => setImportJsonOpen(false)}
        onImported={handleImported}
      />
    </>
  );
}
