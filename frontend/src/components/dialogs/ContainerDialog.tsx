import { useState } from 'react';
import { Dialog } from '../ui/Dialog';
import { FormField } from '../ui/FormField';
import { SelectField } from '../ui/SelectField';
import { isValidIp, isIpInCidr, getNextAvailableIp, getSubnetCapacity } from '../../utils/validation';
import type { Container, ContainerType } from '../../data/sampleTopology';

const typeOptions = [
  { value: 'router', label: 'Router' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'switch', label: 'Switch' },
  { value: 'web-server', label: 'Web Server' },
  { value: 'file-server', label: 'File Server' },
  { value: 'plc', label: 'PLC' },
  { value: 'workstation', label: 'Workstation' },
];

const statusOptions = [
  { value: 'running', label: 'Running' },
  { value: 'stopped', label: 'Stopped' },
  { value: 'paused', label: 'Paused' },
];

interface ContainerDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    type: ContainerType;
    ip: string;
    image: string;
    status: 'running' | 'stopped' | 'paused';
    metadata: Record<string, string>;
  }) => void;
  initial?: Container;
  subnetCidr?: string;
  takenIps?: string[];
}

function ContainerDialogInner({ onClose, onSubmit, initial, subnetCidr, takenIps = [] }: Omit<ContainerDialogProps, 'open'>) {
  const defaultIp = initial?.ip ?? (subnetCidr ? getNextAvailableIp(subnetCidr, takenIps) ?? '' : '');

  const [name, setName] = useState(initial?.name ?? '');
  const [type, setType] = useState<ContainerType>(initial?.type ?? 'workstation');
  const [ip, setIp] = useState(defaultIp);
  const [ipError, setIpError] = useState('');
  const [image, setImage] = useState(initial?.image ?? '');
  const [status, setStatus] = useState<'running' | 'stopped' | 'paused'>(initial?.status ?? 'running');
  const [metaKey, setMetaKey] = useState('');
  const [metaValue, setMetaValue] = useState('');
  const [metadata, setMetadata] = useState<Record<string, string>>(initial?.metadata ? { ...initial.metadata } : {});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (!isValidIp(ip)) {
      setIpError('Invalid IP address');
      return;
    }
    if (subnetCidr && !isIpInCidr(ip, subnetCidr)) {
      setIpError(`IP not in subnet ${subnetCidr}`);
      return;
    }
    // Check for duplicate (skip own IP when editing)
    const isOwnIp = initial && ip.trim() === initial.ip;
    if (!isOwnIp && takenIps.includes(ip.trim())) {
      setIpError('IP already in use');
      return;
    }
    onSubmit({
      name: name.trim(),
      type,
      ip: ip.trim(),
      image: image.trim(),
      status,
      metadata,
    });
    onClose();
  };

  const addMetaEntry = () => {
    if (metaKey.trim() && metaValue.trim()) {
      setMetadata(prev => ({ ...prev, [metaKey.trim()]: metaValue.trim() }));
      setMetaKey('');
      setMetaValue('');
    }
  };

  const removeMetaEntry = (key: string) => {
    setMetadata(prev => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <FormField label="Name" value={name} onChange={setName} placeholder="e.g. Core Router" />
      <SelectField label="Type" value={type} onChange={(v) => setType(v as ContainerType)} options={typeOptions} />
      <FormField
        label="IP Address"
        value={ip}
        onChange={(v) => { setIp(v); setIpError(''); }}
        placeholder="e.g. 10.0.1.1"
        error={ipError}
      />
      {subnetCidr && (() => {
        const cap = getSubnetCapacity(subnetCidr);
        const used = takenIps.length;
        const avail = Math.max(0, cap - used);
        return (
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '15px',
            color: avail === 0 ? 'var(--neon-red)' : 'var(--text-dim)',
            marginTop: '-8px',
            marginBottom: '12px',
          }}>
            {avail === 0 ? 'Subnet full — ' : ''}{used}/{cap} IPs used in {subnetCidr}
          </div>
        );
      })()}
      <FormField label="Image" value={image} onChange={setImage} placeholder="e.g. ubuntu:22.04 (optional)" />
      <SelectField label="Status" value={status} onChange={(v) => setStatus(v as 'running' | 'stopped' | 'paused')} options={statusOptions} />

      {/* Metadata */}
      <div style={{ marginBottom: '16px' }}>
        <label style={{
          display: 'block',
          fontFamily: "var(--font-mono)",
          fontSize: '13px',
          color: 'var(--text-dim)',
          textTransform: 'uppercase',
          letterSpacing: '1px',
          marginBottom: '6px',
        }}>
          Metadata
        </label>
        {Object.entries(metadata).map(([k, v]) => (
          <div key={k} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '4px',
            fontFamily: "var(--font-mono)",
            fontSize: '15px',
            color: 'var(--text-primary)',
            minWidth: 0,
          }}>
            <span style={{ color: 'var(--neon-cyan)', flexShrink: 0 }}>{k}</span>
            <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>=</span>
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v}</span>
            <button
              type="button"
              onClick={() => removeMetaEntry(k)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--neon-red)',
                cursor: 'pointer',
                fontFamily: "var(--font-mono)",
                fontSize: '15px',
                padding: '0 4px',
                flexShrink: 0,
              }}
            >
              x
            </button>
          </div>
        ))}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
          <input
            value={metaKey}
            onChange={(e) => setMetaKey(e.target.value)}
            placeholder="key"
            style={{
              width: '100%',
              boxSizing: 'border-box',
              padding: '6px 8px',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              color: 'var(--text-primary)',
              fontFamily: "var(--font-mono)",
              fontSize: '15px',
              outline: 'none',
            }}
          />
          <input
            value={metaValue}
            onChange={(e) => setMetaValue(e.target.value)}
            placeholder="value"
            style={{
              width: '100%',
              boxSizing: 'border-box',
              padding: '6px 8px',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              color: 'var(--text-primary)',
              fontFamily: "var(--font-mono)",
              fontSize: '15px',
              outline: 'none',
            }}
          />
          <button
            type="button"
            onClick={addMetaEntry}
            style={{
              width: '100%',
              padding: '6px 10px',
              background: 'rgba(0, 212, 255, 0.08)',
              border: '1px solid var(--neon-cyan)',
              borderRadius: '4px',
              color: 'var(--neon-cyan)',
              fontFamily: "var(--font-mono)",
              fontSize: '15px',
              cursor: 'pointer',
            }}
          >
            + Add
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
        <button
          type="button"
          onClick={onClose}
          style={{
            padding: '10px 20px',
            background: 'none',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            color: 'var(--text-secondary)',
            fontFamily: "var(--font-mono)",
            fontSize: '15px',
            cursor: 'pointer',
          }}
        >
          Cancel
        </button>
        <button
          type="submit"
          style={{
            padding: '10px 20px',
            background: 'rgba(0, 255, 159, 0.08)',
            border: '1px solid var(--neon-green)',
            borderRadius: '4px',
            color: 'var(--neon-green)',
            fontFamily: "var(--font-mono)",
            fontSize: '15px',
            cursor: 'pointer',
          }}
        >
          {initial ? 'Save' : 'Add Container'}
        </button>
      </div>
    </form>
  );
}

export function ContainerDialog({ open, onClose, onSubmit, initial, subnetCidr, takenIps }: ContainerDialogProps) {
  return (
    <Dialog title={initial ? 'Edit Container' : 'Add Container'} open={open} onClose={onClose} width={460}>
      {open && <ContainerDialogInner onClose={onClose} onSubmit={onSubmit} initial={initial} subnetCidr={subnetCidr} takenIps={takenIps} />}
    </Dialog>
  );
}
