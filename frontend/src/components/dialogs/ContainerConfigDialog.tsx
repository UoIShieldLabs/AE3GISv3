import React, { useState } from 'react';
import { Dialog } from '../ui/Dialog';
import type { Container } from '../../data/sampleTopology';

interface ContainerConfigDialogProps {
  open: boolean;
  onClose: () => void;
  container: Container | null;
  onSave: (config: Record<string, any>) => void;
}

function ContainerConfigDialogInner({ onClose, container, onSave }: Omit<ContainerConfigDialogProps, 'open'>) {
  // Initialize state directly from the container config
  const [localConfig, setLocalConfig] = useState<Record<string, any>>(container?.config || {});

  if (!container) return null;

  const handleChange = (key: string, value: any) => {
    setLocalConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(localConfig);
    onClose();
  };

  // Shared styles to match your FormField and SelectField aesthetics
  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontFamily: "var(--font-mono)",
    fontSize: '13px',
    color: 'var(--text-dim)',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    marginBottom: '6px',
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    boxSizing: 'border-box',
    padding: '8px 12px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    color: 'var(--text-primary)',
    fontFamily: "var(--font-mono)",
    fontSize: '15px',
    outline: 'none',
  };

  return (
    <form onSubmit={handleSubmit}>

      {/* ── WEB SERVER CONFIGURATION ── */}
      {container.type === 'web-server' && (
        <>
          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>Custom index.html Content</label>
            <textarea 
              value={localConfig.index_html || ''} 
              onChange={(e) => handleChange('index_html', e.target.value)}
              placeholder="<h1>Welcome to the web server!</h1>"
              style={{ ...inputStyle, height: '120px', resize: 'vertical' }}
            />
          </div>
        </>
      )}

      {/* ── FALLBACK FOR UNCONFIGURED TYPES ── */}
      {container.type !== 'firewall' && container.type !== 'web-server' && (
        <div style={{ 
          color: 'var(--text-dim)', 
          marginBottom: '16px',
          fontFamily: 'var(--font-mono)',
          fontSize: '13px',
          padding: '16px',
          border: '1px dashed var(--border-color)',
          borderRadius: '4px',
          textAlign: 'center'
        }}>
          No custom configurations available for {container.type} nodes yet.
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '24px' }}>
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
            background: 'rgba(255, 193, 7, 0.08)',
            border: '1px solid var(--neon-yellow, #ffc107)',
            borderRadius: '4px',
            color: 'var(--neon-yellow, #ffc107)',
            fontFamily: "var(--font-mono)",
            fontSize: '15px',
            cursor: 'pointer',
          }}
        >
          Save Configuration
        </button>
      </div>
    </form>
  );
}

// Wrapper component to utilize the global <Dialog> overlay system
export function ContainerConfigDialog({ open, onClose, container, onSave }: ContainerConfigDialogProps) {
  return (
    <Dialog 
      title={`Configure ${container?.name || 'Node'}`} 
      open={open} 
      onClose={onClose} 
      width={460}
    >
      {open && <ContainerConfigDialogInner onClose={onClose} container={container} onSave={onSave} />}
    </Dialog>
  );
}