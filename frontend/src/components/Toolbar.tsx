import './Toolbar.css';
import type { LayoutMode } from '../utils/autoLayout';

interface ToolbarProps {
  onAdd: () => void;
  addLabel: string;
  onAutoLayout: () => void;
  onBulkAdd?: () => void;
  layoutMode?: LayoutMode;
  onLayoutModeChange?: (mode: LayoutMode) => void;
  onPurdue?: () => void;
  readOnly?: boolean;
}

const layoutModes: { value: LayoutMode; label: string }[] = [
  { value: 'dagre', label: 'Tree' },
  { value: 'circle', label: 'Circle' },
  { value: 'grid', label: 'Grid' },
];

export function Toolbar({ onAdd, addLabel, onAutoLayout, onBulkAdd, layoutMode, onLayoutModeChange, onPurdue, readOnly }: ToolbarProps) {
  return (
    <div className="toolbar">
      {!readOnly && (
        <>
          <button className="toolbar-btn primary" onClick={onAdd}>
            + {addLabel}
          </button>
          {onBulkAdd && (
            <button className="toolbar-btn" onClick={onBulkAdd}>
              + Bulk Add
            </button>
          )}
        </>
      )}
      {layoutMode && onLayoutModeChange ? (
        <select
          className="toolbar-layout-select"
          value={layoutMode}
          onChange={e => {
            onLayoutModeChange(e.target.value as LayoutMode);
            onAutoLayout();
          }}
        >
          {layoutModes.map(m => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      ) : (
        <button className="toolbar-btn" onClick={onAutoLayout}>
          Auto Layout
        </button>
      )}
      {onPurdue && (
        <button className="toolbar-btn btn-purdue" onClick={onPurdue} title="View Purdue Model">
          Purdue
        </button>
      )}
    </div>
  );
}
