import { useState } from 'react';
import { Dialog } from '../ui/Dialog';
import { FormField } from '../ui/FormField';
import { isValidCidr } from '../../utils/validation';
import type { Subnet } from '../../data/sampleTopology';

interface SubnetDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; cidr: string }) => void;
  initial?: Subnet;
}

function SubnetDialogInner({ onClose, onSubmit, initial }: Omit<SubnetDialogProps, 'open'>) {
  const [name, setName] = useState(initial?.name ?? '');
  const [cidr, setCidr] = useState(initial?.cidr ?? '');
  const [cidrError, setCidrError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (!isValidCidr(cidr)) {
      setCidrError('Invalid CIDR (e.g. 10.0.0.0/24)');
      return;
    }
    onSubmit({ name: name.trim(), cidr: cidr.trim() });
    onClose();
  };

  return (
    <form onSubmit={handleSubmit}>
      <FormField label="Name" value={name} onChange={setName} placeholder="e.g. Corporate Network" />
      <FormField
        label="CIDR"
        value={cidr}
        onChange={(v) => { setCidr(v); setCidrError(''); }}
        placeholder="e.g. 10.0.1.0/24"
        error={cidrError}
      />
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
            fontSize: '12px',
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
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          {initial ? 'Save' : 'Add Subnet'}
        </button>
      </div>
    </form>
  );
}

export function SubnetDialog({ open, onClose, onSubmit, initial }: SubnetDialogProps) {
  return (
    <Dialog title={initial ? 'Edit Subnet' : 'Add Subnet'} open={open} onClose={onClose}>
      {open && <SubnetDialogInner onClose={onClose} onSubmit={onSubmit} initial={initial} />}
    </Dialog>
  );
}
