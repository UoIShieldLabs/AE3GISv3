import type { Container } from '../../data/sampleTopology';
import { Dialog } from '../ui/Dialog';

interface RouterActionDialogProps {
  open: boolean;
  container: Container | null;
  onClose: () => void;
  onOpenTerminal: () => void;
  onOpenFirewallRules: () => void;
}

export function RouterActionDialog({
  open,
  container,
  onClose,
  onOpenTerminal,
  onOpenFirewallRules,
}: RouterActionDialogProps) {
  return (
    <Dialog title="Router Actions" open={open} onClose={onClose} width={460}>
      {container && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              color: 'var(--text-secondary)',
            }}
          >
            {container.name} ({container.ip})
          </div>

          <button
            onClick={onOpenTerminal}
            style={{
              padding: '12px',
              background: 'rgba(0, 212, 255, 0.08)',
              border: '1px solid var(--neon-cyan)',
              color: 'var(--neon-cyan)',
              borderRadius: '4px',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              cursor: 'pointer',
            }}
          >
            Open Terminal
          </button>

          <button
            onClick={onOpenFirewallRules}
            style={{
              padding: '12px',
              background: 'rgba(255, 170, 0, 0.08)',
              border: '1px solid #ffaa00',
              color: '#ffaa00',
              borderRadius: '4px',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              cursor: 'pointer',
            }}
          >
            Firewall Rules
          </button>
        </div>
      )}
    </Dialog>
  );
}
