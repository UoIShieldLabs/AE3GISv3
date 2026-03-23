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
  onExport: () => void;
  isBusy: boolean;
  readOnly?: boolean;
}

export function ControlBar({
  backendId,
  backendName,
  deployStatus,
  dirty,
  onNew,
  onSave,
  onLoad,
  onExport,
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
