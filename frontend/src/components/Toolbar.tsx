import './Toolbar.css';
import type { LayoutMode } from '../utils/autoLayout';

interface ToolbarProps {
  onAdd: () => void;
  addLabel: string;
  onAutoLayout: () => void;
  onBulkAdd?: () => void;
  layoutMode?: LayoutMode;
  onLayoutModeChange?: (mode: LayoutMode) => void;
  readOnly?: boolean;
}

const layoutModes: { value: LayoutMode; label: string }[] = [
  { value: 'dagre', label: 'Tree' },
  { value: 'circle', label: 'Circle' },
  { value: 'grid', label: 'Grid' },
];

export function Toolbar({ onAdd, addLabel, onAutoLayout, onBulkAdd, layoutMode, onLayoutModeChange, readOnly }: ToolbarProps) {
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
        <div className="toolbar-layout-group">
          {layoutModes.map(m => (
            <button
              key={m.value}
              className={`toolbar-btn layout-btn${layoutMode === m.value ? ' active' : ''}`}
              onClick={() => {
                onLayoutModeChange(m.value);
                onAutoLayout();
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      ) : (
        <button className="toolbar-btn" onClick={onAutoLayout}>
          Auto Layout
        </button>
      )}
    </div>
  );
}
