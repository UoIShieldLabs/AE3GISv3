import { useEffect, useRef } from 'react';
import './Dialog.css';

interface DialogProps {
  title: string;
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  width?: number;
}

export function Dialog({ title, open, onClose, children, width = 420 }: DialogProps) {
  const mouseDownOnOverlay = useRef(false);

  useEffect(() => {
    if (!open) return;
    const handle = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handle);
    return () => document.removeEventListener('keydown', handle);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="dialog-overlay"
      onMouseDown={(e) => { mouseDownOnOverlay.current = e.target === e.currentTarget; }}
      onClick={() => { if (mouseDownOnOverlay.current) onClose(); }}
    >
      <div
        className="dialog-panel"
        style={{ width }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="dialog-header">
          <div className="dialog-title">{title}</div>
          <button className="dialog-close" onClick={onClose}>x</button>
        </div>
        <div className="dialog-body">
          {children}
        </div>
      </div>
    </div>
  );
}
