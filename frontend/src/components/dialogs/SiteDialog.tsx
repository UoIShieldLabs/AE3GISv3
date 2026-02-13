import { useState } from 'react';
import { Dialog } from '../ui/Dialog';
import { FormField } from '../ui/FormField';
import type { Site } from '../../data/sampleTopology';

interface SiteDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; location: string; posX: number; posY: number }) => void;
  initial?: Site;
}

function SiteDialogInner({ onClose, onSubmit, initial }: Omit<SiteDialogProps, 'open'>) {
  const [name, setName] = useState(initial?.name ?? '');
  const [location, setLocation] = useState(initial?.location ?? '');
  const [posX, setPosX] = useState(initial ? String(initial.position.x) : '');
  const [posY, setPosY] = useState(initial ? String(initial.position.y) : '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSubmit({
      name: name.trim(),
      location: location.trim(),
      posX: posX ? Number(posX) : Math.random() * 500,
      posY: posY ? Number(posY) : Math.random() * 400,
    });
    onClose();
  };

  return (
    <form onSubmit={handleSubmit}>
      <FormField label="Name" value={name} onChange={setName} placeholder="e.g. New York HQ" />
      <FormField label="Location" value={location} onChange={setLocation} placeholder="e.g. New York, NY" />
      <div style={{ display: 'flex', gap: '12px' }}>
        <div style={{ flex: 1 }}>
          <FormField label="Position X" value={posX} onChange={setPosX} placeholder="Auto" type="number" />
        </div>
        <div style={{ flex: 1 }}>
          <FormField label="Position Y" value={posY} onChange={setPosY} placeholder="Auto" type="number" />
        </div>
      </div>
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
          {initial ? 'Save' : 'Add Site'}
        </button>
      </div>
    </form>
  );
}

export function SiteDialog({ open, onClose, onSubmit, initial }: SiteDialogProps) {
  return (
    <Dialog title={initial ? 'Edit Site' : 'Add Site'} open={open} onClose={onClose}>
      {open && <SiteDialogInner onClose={onClose} onSubmit={onSubmit} initial={initial} />}
    </Dialog>
  );
}
