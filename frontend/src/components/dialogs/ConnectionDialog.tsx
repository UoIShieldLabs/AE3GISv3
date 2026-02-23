import { useState } from 'react';
import { Dialog } from '../ui/Dialog';
import { SelectField } from '../ui/SelectField';
import { FormField } from '../ui/FormField';

interface ConnectionDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { from: string; to: string; label: string }) => void;
  availableNodes: { id: string; name: string }[];
}

function ConnectionDialogInner({ onClose, onSubmit, availableNodes }: Omit<ConnectionDialogProps, 'open'>) {
  const [from, setFrom] = useState(availableNodes.length >= 1 ? availableNodes[0].id : '');
  const [to, setTo] = useState(availableNodes.length >= 2 ? availableNodes[1].id : '');
  const [label, setLabel] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!from || !to || from === to) return;
    onSubmit({ from, to, label: label.trim() });
    onClose();
  };

  const nodeOptions = availableNodes.map(n => ({ value: n.id, label: n.name }));

  return (
    <form onSubmit={handleSubmit}>
      <SelectField label="From" value={from} onChange={setFrom} options={nodeOptions} />
      <SelectField label="To" value={to} onChange={setTo} options={nodeOptions} />
      <FormField label="Label (optional)" value={label} onChange={setLabel} placeholder="e.g. MPLS, VPN" />
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
        <button
          type="button"
          onClick={onClose}
          style={{
            padding: '8px 16px',
            background: 'none',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            color: 'var(--text-secondary)',
            fontFamily: "var(--font-mono)",
            fontSize: '13px',
            cursor: 'pointer',
          }}
        >
          Cancel
        </button>
        <button
          type="submit"
          style={{
            padding: '8px 16px',
            background: 'rgba(0, 255, 159, 0.08)',
            border: '1px solid var(--neon-green)',
            borderRadius: '4px',
            color: 'var(--neon-green)',
            fontFamily: "var(--font-mono)",
            fontSize: '13px',
            cursor: 'pointer',
          }}
        >
          Add Connection
        </button>
      </div>
    </form>
  );
}

export function ConnectionDialog({ open, onClose, onSubmit, availableNodes }: ConnectionDialogProps) {
  return (
    <Dialog title="Add Connection" open={open} onClose={onClose}>
      {open && <ConnectionDialogInner onClose={onClose} onSubmit={onSubmit} availableNodes={availableNodes} />}
    </Dialog>
  );
}
