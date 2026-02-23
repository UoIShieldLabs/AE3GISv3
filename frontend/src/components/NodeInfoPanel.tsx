import { useContext, useState } from 'react';
import type { Container, ContainerType } from '../data/sampleTopology';
import { TopologyDispatchContext } from '../store/TopologyContext';
import { ContainerDialog } from './dialogs/ContainerDialog';
import { ConfirmDialog } from './dialogs/ConfirmDialog';

interface NodeInfoPanelProps {
  container: Container | null;
  onClose: () => void;
  onOpenTerminal: (container: Container) => void;
  siteId: string | null;
  subnetId: string | null;
  readOnly?: boolean;
}

const typeDisplayNames: Record<string, string> = {
  'web-server': 'Web Server',
  'file-server': 'File Server',
  'plc': 'PLC Controller',
  'firewall': 'Firewall',
  'switch': 'Network Switch',
  'router': 'Router',
  'workstation': 'Workstation',
};

export function NodeInfoPanel({
  container,
  onClose,
  onOpenTerminal,
  siteId,
  subnetId,
  readOnly,
}: NodeInfoPanelProps) {
  const dispatch = useContext(TopologyDispatchContext);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const handleEdit = (data: {
    name: string; type: ContainerType; ip: string; image: string;
    status: 'running' | 'stopped' | 'paused'; metadata: Record<string, string>;
    persistencePaths: string[];
  }) => {
    if (!container || !siteId || !subnetId) return;
    dispatch({
      type: 'UPDATE_CONTAINER',
      payload: {
        siteId,
        subnetId,
        containerId: container.id,
        updates: {
          name: data.name,
          type: data.type,
          ip: data.ip,
          image: data.image || undefined,
          status: data.status,
          metadata: Object.keys(data.metadata).length > 0 ? data.metadata : undefined,
          persistencePaths: data.persistencePaths.length > 0 ? data.persistencePaths : undefined,
        },
      },
    });
  };

  const handleDelete = () => {
    if (!container || !siteId || !subnetId) return;
    dispatch({
      type: 'DELETE_CONTAINER',
      payload: { siteId, subnetId, containerId: container.id },
    });
    setDeleteOpen(false);
    onClose();
  };

  return (
    <div className={`info-panel ${container ? 'open' : ''}`}>
      {container && (
        <>
          <div className="info-panel-header">
            <div className="info-panel-title">NODE INFO</div>
            <button className="info-panel-close" onClick={onClose}>
              x
            </button>
          </div>

          <div className="info-panel-body">
            <div className="info-field">
              <div className="info-label">Name</div>
              <div className="info-value">{container.name}</div>
            </div>

            <div className="info-field">
              <div className="info-label">Type</div>
              <div className="info-value">
                {typeDisplayNames[container.type] || container.type}
              </div>
            </div>

            <div className="info-field">
              <div className="info-label">IP Address</div>
              <div className="info-value">{container.ip}</div>
            </div>

            {container.image && (
              <div className="info-field">
                <div className="info-label">Image</div>
                <div className="info-value">{container.image}</div>
              </div>
            )}

            {container.status && (
              <div className="info-field">
                <div className="info-label">Status</div>
                <div
                  className={`info-value status-${container.status}`}
                >
                  {container.status.toUpperCase()}
                </div>
              </div>
            )}

            {container.metadata && Object.keys(container.metadata).length > 0 && (
              <>
                <div
                  style={{
                    height: '1px',
                    background: '#1e1e2e',
                    margin: '16px 0',
                  }}
                />
                <div className="info-field">
                  <div className="info-label">Metadata</div>
                </div>
                {Object.entries(container.metadata).map(([key, value]) => (
                  <div className="info-field" key={key}>
                    <div className="info-label">{key}</div>
                    <div className="info-value">{value}</div>
                  </div>
                ))}
              </>
            )}

            {container.persistencePaths && container.persistencePaths.length > 0 && (
              <>
                <div
                  style={{
                    height: '1px',
                    background: '#1e1e2e',
                    margin: '16px 0',
                  }}
                />
                <div className="info-field">
                  <div className="info-label">Persistence Paths</div>
                </div>
                {container.persistencePaths.map((path) => (
                  <div className="info-field" key={path}>
                    <div className="info-value">{path}</div>
                  </div>
                ))}
              </>
            )}
          </div>

          <div className="info-panel-actions">
            <button
              className="btn-terminal"
              onClick={() => onOpenTerminal(container)}
            >
              Open Terminal
            </button>
            {!readOnly && (
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                <button
                  onClick={() => setEditOpen(true)}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    background: 'rgba(0, 212, 255, 0.08)',
                    border: '1px solid var(--neon-cyan)',
                    color: 'var(--neon-cyan)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    cursor: 'pointer',
                    borderRadius: '4px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                  }}
                >
                  Edit
                </button>
                <button
                  onClick={() => setDeleteOpen(true)}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    background: 'rgba(255, 51, 68, 0.08)',
                    border: '1px solid var(--neon-red)',
                    color: 'var(--neon-red)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    cursor: 'pointer',
                    borderRadius: '4px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                  }}
                >
                  Delete
                </button>
              </div>
            )}
          </div>

          {!readOnly && (
            <>
              <ContainerDialog
                open={editOpen}
                onClose={() => setEditOpen(false)}
                onSubmit={handleEdit}
                initial={container}
              />

              <ConfirmDialog
                open={deleteOpen}
                title="Delete Container"
                message={`Delete "${container.name}"? All connections will be removed.`}
                onConfirm={handleDelete}
                onCancel={() => setDeleteOpen(false)}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
