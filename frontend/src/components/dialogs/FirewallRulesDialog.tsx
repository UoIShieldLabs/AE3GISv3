import { useMemo, useState } from 'react';
import type { Container } from '../../data/sampleTopology';
import { Dialog } from '../ui/Dialog';
import { FormField } from '../ui/FormField';
import { SelectField } from '../ui/SelectField';

export type FirewallRule = {
  id: string;
  source: string;
  destination: string;
  protocol: 'any' | 'tcp' | 'udp' | 'icmp';
  port: string;
  action: 'accept' | 'drop';
};

interface FirewallRulesDialogProps {
  open: boolean;
  container: Container | null;
  rules: FirewallRule[];
  onClose: () => void;
  onChangeRules: (rules: FirewallRule[]) => void | Promise<void>;
  onRefresh?: () => void | Promise<void>;
  busy?: boolean;
  error?: string | null;
  readOnly?: boolean;
}

function nextRuleId(): string {
  return `rule-${Math.random().toString(16).slice(2, 10)}`;
}

export function FirewallRulesDialog({
  open,
  container,
  rules,
  onClose,
  onChangeRules,
  onRefresh,
  busy = false,
  error = null,
  readOnly = false,
}: FirewallRulesDialogProps) {
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');
  const [protocol, setProtocol] = useState<'any' | 'tcp' | 'udp' | 'icmp'>('tcp');
  const [port, setPort] = useState('');
  const [action, setAction] = useState<'accept' | 'drop'>('accept');

  const portError = useMemo(() => {
    if (protocol === 'any' || protocol === 'icmp') return '';
    if (!port.trim()) return 'Port is required for TCP/UDP';
    if (!/^\d+$/.test(port.trim())) return 'Port must be numeric';
    const n = Number(port.trim());
    if (n < 1 || n > 65535) return 'Port must be 1-65535';
    return '';
  }, [protocol, port]);

  const canAdd = source.trim() && destination.trim() && !portError;

  const addRule = () => {
    if (!canAdd) return;
    const newRule: FirewallRule = {
      id: nextRuleId(),
      source: source.trim(),
      destination: destination.trim(),
      protocol,
      port: protocol === 'any' || protocol === 'icmp' ? '-' : port.trim(),
      action,
    };
    void onChangeRules([...rules, newRule]);
    setSource('');
    setDestination('');
    setProtocol('tcp');
    setPort('');
    setAction('accept');
  };

  const deleteRule = (id: string) => {
    void onChangeRules(rules.filter((r) => r.id !== id));
  };

  return (
    <Dialog title="Firewall Rules" open={open} onClose={onClose} width={820}>
      {container && (
        <div style={{ display: 'grid', gridTemplateColumns: readOnly ? '1fr' : '1fr 1.2fr', gap: '18px' }}>
          {!readOnly && (
            <div style={{ borderRight: '1px solid var(--border-color)', paddingRight: '18px' }}>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  color: 'var(--text-secondary)',
                  marginBottom: '14px',
                }}
              >
                Target: {container.name} ({container.ip})
              </div>

              <FormField label="Source" value={source} onChange={setSource} placeholder="e.g. 10.0.1.0/24 or any" />
              <FormField label="Destination" value={destination} onChange={setDestination} placeholder="e.g. 10.0.2.10/32" />
              <SelectField
                label="Protocol"
                value={protocol}
                onChange={(v) => setProtocol(v as 'any' | 'tcp' | 'udp' | 'icmp')}
                options={[
                  { value: 'tcp', label: 'TCP' },
                  { value: 'udp', label: 'UDP' },
                  { value: 'icmp', label: 'ICMP' },
                  { value: 'any', label: 'ANY' },
                ]}
              />
              <FormField
                label="Port"
                value={port}
                onChange={setPort}
                placeholder={protocol === 'any' || protocol === 'icmp' ? 'Not used for this protocol' : 'e.g. 443'}
                error={portError || undefined}
              />
              <SelectField
                label="Action"
                value={action}
                onChange={(v) => setAction(v as 'accept' | 'drop')}
                options={[
                  { value: 'accept', label: 'ACCEPT' },
                  { value: 'drop', label: 'DROP' },
                ]}
              />

              <button
                onClick={addRule}
                disabled={!canAdd || busy}
                style={{
                  width: '100%',
                  marginTop: '4px',
                  padding: '11px',
                  background: canAdd && !busy ? 'rgba(0,255,159,0.08)' : 'rgba(80,80,96,0.15)',
                  border: canAdd && !busy ? '1px solid var(--neon-green)' : '1px solid var(--border-color)',
                  color: canAdd && !busy ? 'var(--neon-green)' : 'var(--text-dim)',
                  borderRadius: '4px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  cursor: canAdd && !busy ? 'pointer' : 'not-allowed',
                }}
              >
                {busy ? 'Applying...' : 'Add Rule'}
              </button>

              {onRefresh && (
                <button
                  onClick={() => void onRefresh()}
                  disabled={busy}
                  style={{
                    width: '100%',
                    marginTop: '8px',
                    padding: '9px',
                    background: 'rgba(0, 212, 255, 0.08)',
                    border: '1px solid var(--neon-cyan)',
                    color: 'var(--neon-cyan)',
                    borderRadius: '4px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px',
                    cursor: busy ? 'not-allowed' : 'pointer',
                    opacity: busy ? 0.6 : 1,
                  }}
                >
                  Refresh Running Rules
                </button>
              )}

              {error && (
                <div
                  style={{
                    marginTop: '10px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    color: 'var(--neon-red)',
                  }}
                >
                  {error}
                </div>
              )}
            </div>
          )}

          <div>
            <div
              style={{
                fontFamily: 'var(--font-display)',
                color: 'var(--neon-cyan)',
                fontSize: '12px',
                letterSpacing: '1px',
                marginBottom: '10px',
                textTransform: 'uppercase',
              }}
            >
              Current Rules
            </div>

            {rules.length === 0 ? (
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-dim)' }}>
                No rules configured.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '58vh', overflow: 'auto' }}>
                {rules.map((rule) => (
                  <div
                    key={rule.id}
                    style={{
                      border: '1px solid var(--border-color)',
                      borderRadius: '4px',
                      padding: '10px',
                      background: 'rgba(20,20,30,0.5)',
                    }}
                  >
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto auto auto', gap: '8px', alignItems: 'center' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>{rule.source}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>{rule.destination}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--neon-cyan)' }}>{rule.protocol.toUpperCase()}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-primary)' }}>{rule.port}</div>
                      <div
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '11px',
                          color: rule.action === 'accept' ? 'var(--neon-green)' : 'var(--neon-red)',
                        }}
                      >
                        {rule.action.toUpperCase()}
                      </div>
                      {!readOnly && (
                        <button
                          onClick={() => deleteRule(rule.id)}
                          disabled={busy}
                          style={{
                            background: 'transparent',
                            border: '1px solid var(--border-color)',
                            color: 'var(--text-secondary)',
                            borderRadius: '3px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '10px',
                            textTransform: 'uppercase',
                            letterSpacing: '1px',
                            padding: '5px 7px',
                            cursor: busy ? 'not-allowed' : 'pointer',
                            opacity: busy ? 0.6 : 1,
                          }}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Dialog>
  );
}
