import { useRef, useState } from 'react';
import { Dialog } from '../ui/Dialog';
import { importTopology, type TopologySummary } from '../../api/client';

interface ImportClabDialogProps {
  open: boolean;
  onClose: () => void;
  onImported: (topo: TopologySummary) => void;
}

export function ImportClabDialog({ open, onClose, onImported }: ImportClabDialogProps) {
  const [name, setName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    if (f && !name) {
      // Pre-fill name from filename, stripping .clab.yml / .clab.yaml / .yml / .yaml
      const baseName = f.name.replace(/\.clab\.(ya?ml)$|\.ya?ml$/, '');
      setName(baseName);
    }
    setError(null);
  };

  const handleSubmit = async () => {
    if (!file) { setError('Please select a .clab.yml file.'); return; }
    if (!name.trim()) { setError('Please enter a topology name.'); return; }
    setLoading(true);
    setError(null);
    try {
      const result = await importTopology(name.trim(), file);
      onImported(result);
      handleClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setName('');
    setFile(null);
    setError(null);
    setLoading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onClose();
  };

  const fieldStyle: React.CSSProperties = {
    width: '100%',
    padding: '7px 10px',
    background: 'var(--bg-input, rgba(0,0,0,0.3))',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    boxSizing: 'border-box',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-dim)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '6px',
  };

  return (
    <Dialog title="Import .clab.yml" open={open} onClose={handleClose} width={440}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <label style={labelStyle}>Topology Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="my-topology"
            style={fieldStyle}
            disabled={loading}
          />
        </div>

        <div>
          <label style={labelStyle}>ContainerLab File (.yml / .yaml)</label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".yml,.yaml"
            onChange={handleFileChange}
            disabled={loading}
            style={{
              ...fieldStyle,
              cursor: 'pointer',
              padding: '5px 10px',
            }}
          />
          {file && (
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: 'var(--text-dim)',
              marginTop: '4px',
            }}>
              {file.name}
            </div>
          )}
        </div>

        {error && (
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
            color: 'var(--neon-red)',
            padding: '8px 10px',
            border: '1px solid rgba(255,51,68,0.3)',
            borderRadius: '4px',
            background: 'rgba(255,51,68,0.05)',
          }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            onClick={handleClose}
            disabled={loading}
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
            onClick={handleSubmit}
            disabled={loading || !file}
            style={{
              padding: '8px 16px',
              background: 'rgba(0, 212, 255, 0.08)',
              border: '1px solid var(--neon-cyan)',
              borderRadius: '4px',
              color: 'var(--neon-cyan)',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              cursor: loading || !file ? 'not-allowed' : 'pointer',
              opacity: loading || !file ? 0.5 : 1,
            }}
          >
            {loading ? 'Importing…' : 'Import'}
          </button>
        </div>
      </div>
    </Dialog>
  );
}
