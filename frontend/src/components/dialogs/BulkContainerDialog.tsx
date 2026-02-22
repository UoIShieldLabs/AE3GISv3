import { useState, useCallback, useMemo } from 'react';
import { Dialog } from '../ui/Dialog';
import { FormField } from '../ui/FormField';
import { SelectField } from '../ui/SelectField';
import { isValidIp, isIpInCidr, getAvailableIps, getSubnetCapacity } from '../../utils/validation';
import type { ContainerType } from '../../data/sampleTopology';

const typeOptions = [
  { value: 'router', label: 'Router' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'switch', label: 'Switch' },
  { value: 'web-server', label: 'Web Server' },
  { value: 'file-server', label: 'File Server' },
  { value: 'plc', label: 'PLC' },
  { value: 'workstation', label: 'Workstation' },
];

interface BulkEntry {
  key: number;
  name: string;
  type: ContainerType;
  ip: string;
}

interface BulkContainerDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (entries: { name: string; type: ContainerType; ip: string }[]) => void;
  subnetCidr: string;
  takenIps: string[];
}

let nextKey = 0;

function BulkContainerDialogInner({ onClose, onSubmit, subnetCidr, takenIps }: Omit<BulkContainerDialogProps, 'open'>) {
  // Generator fields
  const [prefix, setPrefix] = useState('Container');
  const [genType, setGenType] = useState<ContainerType>('workstation');
  const [count, setCount] = useState('5');
  const [genError, setGenError] = useState('');

  // Table entries
  const [entries, setEntries] = useState<BulkEntry[]>([]);

  // Subnet capacity
  const totalCapacity = useMemo(() => getSubnetCapacity(subnetCidr), [subnetCidr]);
  const pendingCount = useMemo(
    () => entries.filter(e => isValidIp(e.ip)).length,
    [entries]
  );
  const usedCount = takenIps.length;
  const availableCount = Math.max(0, totalCapacity - usedCount - pendingCount);

  const handleGenerate = useCallback(() => {
    const n = parseInt(count, 10);
    if (isNaN(n) || n < 1 || n > 500) {
      setGenError('Count must be 1–500');
      return;
    }

    const currentTaken = [...takenIps, ...entries.map(e => e.ip).filter(ip => isValidIp(ip))];
    const ips = getAvailableIps(subnetCidr, currentTaken, n);
    if (ips.length === 0) {
      setGenError('No available IPs in subnet');
      return;
    }
    if (ips.length < n) {
      setGenError(`Only ${ips.length} IPs available (requested ${n})`);
    } else {
      setGenError('');
    }
    const generated: BulkEntry[] = ips.map((ip, i) => ({
      key: nextKey++,
      name: `${prefix} ${i + 1}`,
      type: genType,
      ip,
    }));
    setEntries(prev => [...prev, ...generated]);
  }, [prefix, genType, count, subnetCidr, takenIps, entries]);

  const handleAddRow = useCallback(() => {
    setEntries(prev => [...prev, { key: nextKey++, name: '', type: 'workstation', ip: '' }]);
  }, []);

  const updateEntry = useCallback((key: number, field: keyof BulkEntry, value: string) => {
    setEntries(prev => prev.map(e =>
      e.key === key ? { ...e, [field]: value } : e
    ));
  }, []);

  const removeEntry = useCallback((key: number) => {
    setEntries(prev => prev.filter(e => e.key !== key));
  }, []);

  const clearAll = useCallback(() => setEntries([]), []);

  const isEntryValid = useCallback((entry: BulkEntry) => {
    if (!entry.name.trim() || !isValidIp(entry.ip)) return false;
    if (!isIpInCidr(entry.ip, subnetCidr)) return false;
    if (takenIps.includes(entry.ip.trim())) return false;
    // Check for intra-table duplicates — only the first occurrence is valid
    const firstWithIp = entries.find(e => e.ip.trim() === entry.ip.trim());
    if (firstWithIp && firstWithIp.key !== entry.key) return false;
    return true;
  }, [subnetCidr, takenIps, entries]);

  const getIpError = useCallback((entry: BulkEntry): string => {
    if (!entry.ip) return '';
    if (!isValidIp(entry.ip)) return 'Invalid IP';
    if (!isIpInCidr(entry.ip, subnetCidr)) return 'Outside subnet';
    if (takenIps.includes(entry.ip.trim())) return 'Already taken';
    // Check for duplicates within the entries themselves
    const dupes = entries.filter(e => e.key !== entry.key && e.ip.trim() === entry.ip.trim());
    if (dupes.length > 0) return 'Duplicate';
    return '';
  }, [subnetCidr, takenIps, entries]);

  const handleSubmit = () => {
    const valid = entries.filter(isEntryValid);
    if (valid.length === 0) return;
    // Final dedup safety net — keep first occurrence of each IP
    const seen = new Set<string>();
    const deduped = valid.filter(e => {
      const ip = e.ip.trim();
      if (seen.has(ip)) return false;
      seen.add(ip);
      return true;
    });
    if (deduped.length === 0) return;
    onSubmit(deduped.map(e => ({ name: e.name.trim(), type: e.type, ip: e.ip.trim() })));
    onClose();
  };

  const validCount = entries.filter(isEntryValid).length;

  const inputStyle: React.CSSProperties = {
    padding: '4px 6px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '3px',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    outline: 'none',
    width: '100%',
  };

  const selectStyle: React.CSSProperties = {
    ...inputStyle,
    appearance: 'none' as const,
    cursor: 'pointer',
  };

  return (
    <div>
      {/* Generator section */}
      <div style={{
        padding: '12px',
        background: 'rgba(0, 255, 159, 0.03)',
        border: '1px solid rgba(0, 255, 159, 0.15)',
        borderRadius: '6px',
        marginBottom: '16px',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '10px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--neon-green)',
            textTransform: 'uppercase',
            letterSpacing: '1px',
          }}>
            Quick Generate
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--text-dim)',
            textAlign: 'right',
          }}>
            <div>{subnetCidr}</div>
            <div style={{ color: availableCount === 0 ? 'var(--neon-red)' : 'var(--text-dim)' }}>
              {usedCount + pendingCount}/{totalCapacity} used — {availableCount} available
            </div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <FormField label="Name prefix" value={prefix} onChange={setPrefix} placeholder="e.g. Server" />
          <SelectField label="Type" value={genType} onChange={v => setGenType(v as ContainerType)} options={typeOptions} />
          <FormField label="Count" value={count} onChange={v => { setCount(v); setGenError(''); }} placeholder="1–500" type="number" />
        </div>
        {genError && (
          <div style={{ color: 'var(--neon-red)', fontFamily: 'var(--font-mono)', fontSize: '11px', marginTop: '6px' }}>
            {genError}
          </div>
        )}
        <button
          type="button"
          onClick={handleGenerate}
          disabled={availableCount === 0}
          style={{
            marginTop: '10px',
            padding: '6px 14px',
            background: availableCount > 0 ? 'rgba(0, 255, 159, 0.08)' : 'transparent',
            border: `1px solid ${availableCount > 0 ? 'var(--neon-green)' : 'var(--border-color)'}`,
            borderRadius: '4px',
            color: availableCount > 0 ? 'var(--neon-green)' : 'var(--text-dim)',
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            cursor: availableCount > 0 ? 'pointer' : 'default',
            opacity: availableCount > 0 ? 1 : 0.5,
          }}
        >
          {availableCount === 0 ? 'Subnet full' : `Generate ${count && !isNaN(Number(count)) ? `(${count})` : ''}`}
        </button>
      </div>

      {/* Entries table */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        color: 'var(--text-dim)',
        textTransform: 'uppercase',
        letterSpacing: '1px',
        marginBottom: '6px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span>Entries ({entries.length})</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          {entries.length > 0 && (
            <button
              type="button"
              onClick={clearAll}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--neon-red)',
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                cursor: 'pointer',
                textTransform: 'uppercase',
              }}
            >
              Clear all
            </button>
          )}
          <button
            type="button"
            onClick={handleAddRow}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--neon-cyan)',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              cursor: 'pointer',
              textTransform: 'uppercase',
            }}
          >
            + Add row
          </button>
        </div>
      </div>

      {entries.length > 0 ? (
        <div style={{
          maxHeight: '280px',
          overflowY: 'auto',
          border: '1px solid var(--border-color)',
          borderRadius: '4px',
        }}>
          {/* Table header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '2fr 1.5fr 1.5fr 28px',
            gap: '6px',
            padding: '6px 8px',
            background: 'rgba(0, 212, 255, 0.05)',
            borderBottom: '1px solid var(--border-color)',
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            color: 'var(--text-dim)',
            textTransform: 'uppercase',
            letterSpacing: '1px',
            position: 'sticky',
            top: 0,
          }}>
            <span>Name</span>
            <span>Type</span>
            <span>IP</span>
            <span />
          </div>

          {/* Table rows */}
          {entries.map((entry) => (
            <div
              key={entry.key}
              style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1.5fr 1.5fr 28px',
                gap: '6px',
                padding: '4px 8px',
                alignItems: 'center',
                borderBottom: '1px solid rgba(255,255,255,0.03)',
              }}
            >
              <input
                value={entry.name}
                onChange={e => updateEntry(entry.key, 'name', e.target.value)}
                style={{
                  ...inputStyle,
                  borderColor: !entry.name.trim() ? 'var(--neon-red)' : 'var(--border-color)',
                }}
                placeholder="Name"
              />
              <select
                value={entry.type}
                onChange={e => updateEntry(entry.key, 'type', e.target.value)}
                style={selectStyle}
              >
                {typeOptions.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <input
                value={entry.ip}
                onChange={e => updateEntry(entry.key, 'ip', e.target.value)}
                title={getIpError(entry) || undefined}
                style={{
                  ...inputStyle,
                  borderColor: getIpError(entry) ? 'var(--neon-red)' : 'var(--border-color)',
                }}
                placeholder="IP"
              />
              <button
                type="button"
                onClick={() => removeEntry(entry.key)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--neon-red)',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  padding: '0',
                  lineHeight: 1,
                }}
              >
                x
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div style={{
          padding: '24px',
          textAlign: 'center',
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          color: 'var(--text-dim)',
          border: '1px dashed var(--border-color)',
          borderRadius: '4px',
        }}>
          No entries yet. Use Generate or Add Row above.
        </div>
      )}

      {/* Footer */}
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '16px' }}>
        <button
          type="button"
          onClick={onClose}
          style={{
            padding: '8px 16px',
            background: 'none',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={validCount === 0}
          style={{
            padding: '8px 16px',
            background: validCount > 0 ? 'rgba(0, 255, 159, 0.08)' : 'transparent',
            border: `1px solid ${validCount > 0 ? 'var(--neon-green)' : 'var(--border-color)'}`,
            borderRadius: '4px',
            color: validCount > 0 ? 'var(--neon-green)' : 'var(--text-dim)',
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
            cursor: validCount > 0 ? 'pointer' : 'default',
            opacity: validCount > 0 ? 1 : 0.5,
          }}
        >
          Add {validCount > 0 ? `${validCount} Container${validCount > 1 ? 's' : ''}` : 'Containers'}
        </button>
      </div>
    </div>
  );
}

export function BulkContainerDialog({ open, onClose, onSubmit, subnetCidr, takenIps }: BulkContainerDialogProps) {
  return (
    <Dialog title="Bulk Add Containers" open={open} onClose={onClose} width={620}>
      {open && <BulkContainerDialogInner onClose={onClose} onSubmit={onSubmit} subnetCidr={subnetCidr} takenIps={takenIps} />}
    </Dialog>
  );
}
