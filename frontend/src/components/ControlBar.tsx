import { useState } from 'react';
import type { DeployStatus } from '../store/topologyReducer';
import { Dialog } from './ui/Dialog';
import { FormField } from './ui/FormField';
import './ControlBar.css';

interface ControlBarProps {
  backendId: string | null;
  backendName: string | null;
  deployStatus: DeployStatus;
  dirty: boolean;
  onNew: () => void;
  onSave: (name?: string) => void;
  onLoad: () => void;
  onDeploy: () => void;
  onDestroy: () => void;
  onExport: () => void;
  onClassroom?: () => void;
  isBusy: boolean;
  readOnly?: boolean;
}

const statusLabels: Record<DeployStatus, string> = {
  idle: 'Idle',
  deployed: 'Deployed',
  deploying: 'Deploying...',
  destroying: 'Destroying...',
  error: 'Error',
};

export function ControlBar({
  backendId,
  backendName,
  deployStatus,
  dirty,
  onNew,
  onSave,
  onLoad,
  onDeploy,
  onDestroy,
  onExport,
  onClassroom,
  isBusy,
  readOnly,
}: ControlBarProps) {
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState('');

  const isTransitioning = deployStatus === 'deploying' || deployStatus === 'destroying';

  const handleSaveClick = () => {
    if (backendId) {
      onSave();
    } else {
      setSaveName(backendName || '');
      setSaveDialogOpen(true);
    }
  };

  const handleSaveConfirm = () => {
    if (!saveName.trim()) return;
    setSaveDialogOpen(false);
    onSave(saveName.trim());
  };

  return (
    <>
      <div className="control-bar">
        <div className={`control-bar-status status-${deployStatus}`}>
          <span className="status-dot" />
          <span>{statusLabels[deployStatus]}</span>
        </div>

        {!readOnly && (
          <>
            <button
              className="control-btn"
              onClick={onNew}
              disabled={isBusy || isTransitioning}
              title="Create a new empty topology"
            >
              New
            </button>

            <button
              className="control-btn btn-save"
              onClick={handleSaveClick}
              disabled={isBusy || isTransitioning}
              title={backendId ? `Save to "${backendName}"` : 'Save as new topology'}
            >
              {dirty ? 'Save*' : 'Save'}
            </button>

            <button
              className="control-btn"
              onClick={onLoad}
              disabled={isBusy || isTransitioning}
              title="Load a saved topology"
            >
              Load
            </button>

            <button
              className="control-btn btn-deploy"
              onClick={onDeploy}
              disabled={isBusy || !backendId || deployStatus !== 'idle'}
              title={!backendId ? 'Save first to deploy' : 'Deploy to ContainerLab'}
            >
              Deploy
            </button>

            <button
              className="control-btn btn-destroy"
              onClick={onDestroy}
              disabled={isBusy || (deployStatus !== 'deployed' && deployStatus !== 'error')}
              title="Destroy running network"
            >
              Destroy
            </button>

            {onClassroom && (
              <button
                className="control-btn btn-classroom"
                onClick={onClassroom}
                disabled={isBusy}
                title="Manage classroom sessions"
              >
                Classroom
              </button>
            )}
          </>
        )}

        <button
          className="control-btn btn-export"
          onClick={onExport}
          disabled={isBusy}
          title="Download topology JSON"
        >
          Export
        </button>
      </div>

      <Dialog
        title="Save Topology"
        open={saveDialogOpen}
        onClose={() => setSaveDialogOpen(false)}
        width={360}
      >
        <div className="save-dialog-body">
          <FormField
            label="Topology Name"
            value={saveName}
            onChange={setSaveName}
            placeholder="e.g. Production Network"
          />
          <div className="save-dialog-actions">
            <button className="btn-cancel" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </button>
            <button
              className="btn-confirm"
              onClick={handleSaveConfirm}
              disabled={!saveName.trim()}
            >
              Save
            </button>
          </div>
        </div>
      </Dialog>
    </>
  );
}
