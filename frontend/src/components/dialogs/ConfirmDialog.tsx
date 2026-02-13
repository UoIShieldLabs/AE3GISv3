import { Dialog } from '../ui/Dialog';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, message, onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <Dialog title={title} open={open} onClose={onCancel} width={360}>
      <div style={{
        fontFamily: "var(--font-mono)",
        fontSize: '13px',
        color: 'var(--text-primary)',
        marginBottom: '20px',
        lineHeight: 1.5,
      }}>
        {message}
      </div>
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
        <button
          onClick={onCancel}
          style={{
            padding: '8px 16px',
            background: 'none',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            color: 'var(--text-secondary)',
            fontFamily: "var(--font-mono)",
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          style={{
            padding: '8px 16px',
            background: 'rgba(255, 51, 68, 0.1)',
            border: '1px solid var(--neon-red)',
            borderRadius: '4px',
            color: 'var(--neon-red)',
            fontFamily: "var(--font-mono)",
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          Delete
        </button>
      </div>
    </Dialog>
  );
}
