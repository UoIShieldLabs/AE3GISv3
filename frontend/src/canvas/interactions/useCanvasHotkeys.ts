import { useEffect } from 'react';
import { useReactFlow } from '@xyflow/react';
import { hasMod, isEditableTarget } from '@/lib/keyboard';

export interface CanvasHotkeyHandlers {
  deleteSelection: () => void;
  duplicateSelection: () => void;
  selectAll: () => void;
  clearSelection: () => void;
  undo: () => void;
  redo: () => void;
  save?: () => void;
  autoLayout: () => void;
  toggleExpandSelection: () => void;
  openSelection: () => void;
  commandPalette?: () => void;
  toggleSidebar?: () => void;
  toggleInspector?: () => void;
}

/** Global editor shortcuts, ignored while typing in inputs or inside overlays. */
export function useCanvasHotkeys(h: CanvasHotkeyHandlers) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isEditableTarget(e)) return;
      const mod = hasMod(e);
      const key = e.key.toLowerCase();

      if (mod && key === 'z') { e.preventDefault(); if (e.shiftKey) h.redo(); else h.undo(); return; }
      if (mod && key === 'y') { e.preventDefault(); h.redo(); return; }
      if (mod && key === 'a') { e.preventDefault(); h.selectAll(); return; }
      if (mod && key === 'd') { e.preventDefault(); h.duplicateSelection(); return; }
      if (mod && key === 's') { e.preventDefault(); h.save?.(); return; }
      if (mod && key === 'k') { e.preventDefault(); h.commandPalette?.(); return; }
      if (mod && key === 'b') { e.preventDefault(); h.toggleSidebar?.(); return; }
      if (mod && key === 'i') { e.preventDefault(); h.toggleInspector?.(); return; }
      if (mod && (key === '=' || key === '+')) { e.preventDefault(); void zoomIn(); return; }
      if (mod && key === '-') { e.preventDefault(); void zoomOut(); return; }
      if (mod && key === '0') { e.preventDefault(); void fitView({ padding: 0.2, maxZoom: 1.25, duration: 200 }); return; }
      if (mod || e.altKey) return;

      switch (key) {
        case 'delete':
        case 'backspace':
          e.preventDefault(); h.deleteSelection(); break;
        case 'escape':
          h.clearSelection(); break;
        case 'f':
          void fitView({ padding: 0.2, maxZoom: 1.25, duration: 200 }); break;
        case 'l':
          h.autoLayout(); break;
        case 'e':
          h.toggleExpandSelection(); break;
        case 'enter':
          h.openSelection(); break;
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [h, fitView, zoomIn, zoomOut]);
}
