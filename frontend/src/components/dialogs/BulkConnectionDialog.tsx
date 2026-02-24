import { useState, useCallback, useMemo } from 'react';
import { Dialog } from '../ui/Dialog';

interface BulkConnectionEntry {
  key: number;
  from: string;
  to: string;
}

interface BulkConnectionDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (connections: { from: string; to: string }[]) => void;
  availableNodes: { id: string; name: string }[];
  existingConnections: { from: string; to: string }[];
}

let nextKey = 0;

type Mode = 'mesh' | 'star' | 'chain';

function BulkConnectionDialogInner({
  onClose,
  onSubmit,
  availableNodes,
  existingConnections,
}: Omit<BulkConnectionDialogProps, 'open'>) {
  const [mode, setMode] = useState<Mode>('star');

  // Star mode
  const [hubId, setHubId] = useState(availableNodes[0]?.id ?? '');
  const [excludedTargets, setExcludedTargets] = useState<Set<string>>(new Set());

  // Chain mode
  const [chainIds, setChainIds] = useState<string[]>([]);

  // Pending connections table
  const [entries, setEntries] = useState<BulkConnectionEntry[]>([]);

  // Build lookup set of existing connections (bidirectional)
  const existingSet = useMemo(() => {
    const s = new Set<string>();
    for (const c of existingConnections) {
      s.add(`${c.from}|${c.to}`);
      s.add(`${c.to}|${c.from}`);
    }
    return s;
  }, [existingConnections]);

  // Also track what's already in the entries table
  const entrySet = useMemo(() => {
    const s = new Set<string>();
    for (const e of entries) {
      s.add(`${e.from}|${e.to}`);
      s.add(`${e.to}|${e.from}`);
    }
    return s;
  }, [entries]);

  const isDuplicate = useCallback(
    (from: string, to: string) =>
      existingSet.has(`${from}|${to}`) || entrySet.has(`${from}|${to}`),
    [existingSet, entrySet]
  );

  const nodeNameMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const n of availableNodes) m.set(n.id, n.name);
    return m;
  }, [availableNodes]);

  // Star: toggle excluded target (inverted logic — all included by default)
  const toggleExcluded = useCallback((id: string) => {
    setExcludedTargets(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // Chain: add node to chain
  const addToChain = useCallback((id: string) => {
    setChainIds(prev => [...prev, id]);
  }, []);

  const removeFromChain = useCallback((idx: number) => {
    setChainIds(prev => prev.filter((_, i) => i !== idx));
  }, []);

  const clearChain = useCallback(() => setChainIds([]), []);

  // Preview counts for each mode
  const meshPreview = useMemo(() => {
    let count = 0;
    for (let i = 0; i < availableNodes.length; i++) {
      for (let j = i + 1; j < availableNodes.length; j++) {
        const a = availableNodes[i].id;
        const b = availableNodes[j].id;
        if (!isDuplicate(a, b)) count++;
      }
    }
    return count;
  }, [availableNodes, isDuplicate]);

  const starPreview = useMemo(() => {
    if (!hubId) return 0;
    let count = 0;
    for (const n of availableNodes) {
      if (n.id === hubId || excludedTargets.has(n.id)) continue;
      if (!isDuplicate(hubId, n.id)) count++;
    }
    return count;
  }, [availableNodes, hubId, excludedTargets, isDuplicate]);

  const chainPreview = useMemo(() => {
    let count = 0;
    for (let i = 0; i < chainIds.length - 1; i++) {
      if (chainIds[i] !== chainIds[i + 1] && !isDuplicate(chainIds[i], chainIds[i + 1])) {
        count++;
      }
    }
    return count;
  }, [chainIds, isDuplicate]);

  // Generate connections from pattern
  const handleGenerate = useCallback(() => {
    const newEntries: BulkConnectionEntry[] = [];

    if (mode === 'mesh') {
      for (let i = 0; i < availableNodes.length; i++) {
        for (let j = i + 1; j < availableNodes.length; j++) {
          const a = availableNodes[i].id;
          const b = availableNodes[j].id;
          if (!isDuplicate(a, b)) {
            newEntries.push({ key: nextKey++, from: a, to: b });
          }
        }
      }
    } else if (mode === 'star') {
      if (!hubId) return;
      for (const n of availableNodes) {
        if (n.id === hubId || excludedTargets.has(n.id)) continue;
        if (!isDuplicate(hubId, n.id)) {
          newEntries.push({ key: nextKey++, from: hubId, to: n.id });
        }
      }
    } else {
      // Chain: connect sequentially
      for (let i = 0; i < chainIds.length - 1; i++) {
        const from = chainIds[i];
        const to = chainIds[i + 1];
        if (from === to) continue;
        if (!isDuplicate(from, to)) {
          newEntries.push({ key: nextKey++, from, to });
        }
      }
    }

    if (newEntries.length > 0) {
      setEntries(prev => [...prev, ...newEntries]);
    }
  }, [mode, availableNodes, hubId, excludedTargets, chainIds, isDuplicate]);

  const handleAddRow = useCallback(() => {
    const from = availableNodes[0]?.id ?? '';
    const to = availableNodes[1]?.id ?? availableNodes[0]?.id ?? '';
    setEntries(prev => [...prev, { key: nextKey++, from, to }]);
  }, [availableNodes]);

  const updateEntry = useCallback((key: number, field: 'from' | 'to', value: string) => {
    setEntries(prev => prev.map(e => (e.key === key ? { ...e, [field]: value } : e)));
  }, []);

  const removeEntry = useCallback((key: number) => {
    setEntries(prev => prev.filter(e => e.key !== key));
  }, []);

  const clearAll = useCallback(() => setEntries([]), []);

  const handleSubmit = () => {
    // Filter out self-connections and true duplicates within the batch
    const seen = new Set<string>();
    const valid: { from: string; to: string }[] = [];
    for (const e of entries) {
      if (e.from === e.to) continue;
      const biKey = [e.from, e.to].sort().join('|');
      if (seen.has(biKey)) continue;
      if (existingSet.has(`${e.from}|${e.to}`)) continue;
      seen.add(biKey);
      valid.push({ from: e.from, to: e.to });
    }
    if (valid.length === 0) return;
    onSubmit(valid);
    onClose();
  };

  // Count valid (non-duplicate, non-self) entries
  const validCount = useMemo(() => {
    const seen = new Set<string>();
    let count = 0;
    for (const e of entries) {
      if (e.from === e.to) continue;
      const biKey = [e.from, e.to].sort().join('|');
      if (seen.has(biKey)) continue;
      if (existingSet.has(`${e.from}|${e.to}`)) continue;
      seen.add(biKey);
      count++;
    }
    return count;
  }, [entries, existingSet]);

  const inputStyle: React.CSSProperties = {
    padding: '4px 6px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '3px',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    outline: 'none',
    width: '100%',
    appearance: 'none' as const,
    cursor: 'pointer',
  };

  const nodesNotInChain = availableNodes.filter(n => !chainIds.includes(n.id));

  const currentPreview = mode === 'mesh' ? meshPreview : mode === 'star' ? starPreview : chainPreview;

  return (
    <div>
      {/* Pattern generator */}
      <div style={{
        padding: '12px',
        background: 'rgba(0, 212, 255, 0.03)',
        border: '1px solid rgba(0, 212, 255, 0.15)',
        borderRadius: '6px',
        marginBottom: '16px',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
          color: 'var(--neon-cyan)',
          textTransform: 'uppercase',
          letterSpacing: '1px',
          marginBottom: '10px',
        }}>
          Quick Connect
        </div>

        {/* Mode tabs */}
        <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
          {([
            { key: 'mesh' as Mode, label: 'Mesh (All ↔ All)' },
            { key: 'star' as Mode, label: 'Star (Hub → Many)' },
            { key: 'chain' as Mode, label: 'Chain (A → B → C)' },
          ]).map(m => (
            <button
              key={m.key}
              type="button"
              onClick={() => setMode(m.key)}
              style={{
                padding: '5px 12px',
                background: mode === m.key ? 'rgba(0, 212, 255, 0.12)' : 'transparent',
                border: `1px solid ${mode === m.key ? 'var(--neon-cyan)' : 'var(--border-color)'}`,
                borderRadius: '4px',
                color: mode === m.key ? 'var(--neon-cyan)' : 'var(--text-dim)',
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              {m.label}
            </button>
          ))}
        </div>

        {mode === 'mesh' ? (
          <div style={{
            padding: '10px',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
            color: 'var(--text-secondary)',
          }}>
            Connects every node to every other node.
            <br />
            <span style={{ color: 'var(--neon-cyan)', fontSize: '12px' }}>
              {availableNodes.length} nodes → {meshPreview} new connection{meshPreview !== 1 ? 's' : ''}
            </span>
            {meshPreview === 0 && availableNodes.length > 1 && (
              <span style={{ color: 'var(--text-dim)', fontSize: '12px', display: 'block', marginTop: '4px' }}>
                (all pairs already connected)
              </span>
            )}
          </div>
        ) : mode === 'star' ? (
          <div>
            {/* Hub selector */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                color: 'var(--text-dim)',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                marginBottom: '4px',
              }}>
                Hub Node
              </div>
              <select
                value={hubId}
                onChange={e => {
                  setHubId(e.target.value);
                  setExcludedTargets(new Set());
                }}
                style={{ ...inputStyle, padding: '6px 8px', fontSize: '12px' }}
              >
                {availableNodes.map(n => (
                  <option key={n.id} value={n.id}>{n.name}</option>
                ))}
              </select>
            </div>

            {/* Summary + optional exclusion list */}
            <div style={{
              padding: '8px',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              color: 'var(--text-secondary)',
              marginBottom: '4px',
            }}>
              Connects hub to {availableNodes.length - 1 - excludedTargets.size} of {availableNodes.length - 1} target{availableNodes.length - 1 !== 1 ? 's' : ''} →{' '}
              <span style={{ color: 'var(--neon-cyan)' }}>{starPreview} new</span>
              {excludedTargets.size > 0 && (
                <span style={{ color: 'var(--text-dim)' }}> ({excludedTargets.size} excluded)</span>
              )}
            </div>

            {/* Compact exclusion toggle list */}
            <details style={{ marginTop: '6px' }}>
              <summary style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                color: 'var(--text-dim)',
                cursor: 'pointer',
                textTransform: 'uppercase',
                letterSpacing: '1px',
              }}>
                Exclude specific nodes
              </summary>
              <div style={{
                maxHeight: '120px',
                overflowY: 'auto',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                padding: '4px',
                marginTop: '6px',
              }}>
                {availableNodes.filter(n => n.id !== hubId).map(n => {
                  const alreadyExists = existingSet.has(`${hubId}|${n.id}`);
                  const isExcluded = excludedTargets.has(n.id);
                  return (
                    <label
                      key={n.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '3px 6px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '13px',
                        color: alreadyExists ? 'var(--text-dim)' : isExcluded ? 'var(--text-dim)' : 'var(--text-primary)',
                        cursor: alreadyExists ? 'default' : 'pointer',
                        opacity: alreadyExists ? 0.4 : isExcluded ? 0.6 : 1,
                        borderRadius: '3px',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isExcluded}
                        onChange={() => toggleExcluded(n.id)}
                        disabled={alreadyExists}
                        style={{ accentColor: 'var(--neon-red)' }}
                      />
                      {n.name}
                      {alreadyExists && (
                        <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginLeft: 'auto' }}>
                          exists
                        </span>
                      )}
                    </label>
                  );
                })}
              </div>
            </details>
          </div>
        ) : (
          <div>
            {/* Chain builder */}
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              color: 'var(--text-dim)',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              marginBottom: '6px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <span>Chain Order ({chainIds.length} nodes → {chainPreview} new)</span>
              {chainIds.length > 0 && (
                <button type="button" onClick={clearChain} style={{
                  background: 'none', border: 'none', color: 'var(--neon-red)',
                  fontFamily: 'var(--font-mono)', fontSize: '11px', cursor: 'pointer', textTransform: 'uppercase',
                }}>Clear</button>
              )}
            </div>

            {/* Current chain display */}
            {chainIds.length > 0 && (
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '4px',
                marginBottom: '8px',
                padding: '8px',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                alignItems: 'center',
              }}>
                {chainIds.map((id, idx) => (
                  <span key={idx} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {idx > 0 && (
                      <span style={{ color: 'var(--neon-cyan)', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                        →
                      </span>
                    )}
                    <span
                      style={{
                        padding: '3px 8px',
                        background: 'rgba(0, 212, 255, 0.08)',
                        border: '1px solid rgba(0, 212, 255, 0.3)',
                        borderRadius: '3px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '12px',
                        color: 'var(--neon-cyan)',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      {nodeNameMap.get(id) ?? id}
                      <button
                        type="button"
                        onClick={() => removeFromChain(idx)}
                        style={{
                          background: 'none', border: 'none', color: 'var(--neon-red)',
                          cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '12px',
                          padding: 0, lineHeight: 1,
                        }}
                      >
                        x
                      </button>
                    </span>
                  </span>
                ))}
              </div>
            )}

            {/* Available nodes to add to chain */}
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              color: 'var(--text-dim)',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              marginBottom: '4px',
            }}>
              Click to add to chain
            </div>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '4px',
              maxHeight: '100px',
              overflowY: 'auto',
              padding: '4px',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
            }}>
              {nodesNotInChain.length > 0 ? nodesNotInChain.map(n => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => addToChain(n.id)}
                  style={{
                    padding: '3px 8px',
                    background: 'transparent',
                    border: '1px solid var(--border-color)',
                    borderRadius: '3px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                  }}
                >
                  + {n.name}
                </button>
              )) : (
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  color: 'var(--text-dim)',
                  padding: '4px',
                }}>
                  All nodes added to chain
                </span>
              )}
            </div>
          </div>
        )}

        {/* Generate button */}
        <button
          type="button"
          onClick={handleGenerate}
          disabled={currentPreview === 0}
          style={{
            marginTop: '10px',
            padding: '6px 14px',
            background: currentPreview > 0 ? 'rgba(0, 212, 255, 0.08)' : 'transparent',
            border: `1px solid ${currentPreview > 0 ? 'var(--neon-cyan)' : 'var(--border-color)'}`,
            borderRadius: '4px',
            color: currentPreview > 0 ? 'var(--neon-cyan)' : 'var(--text-dim)',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
            cursor: currentPreview > 0 ? 'pointer' : 'default',
            opacity: currentPreview > 0 ? 1 : 0.5,
          }}
        >
          Generate {currentPreview > 0 ? `(${currentPreview})` : ''}
        </button>
      </div>

      {/* Entries table */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '12px',
        color: 'var(--text-dim)',
        textTransform: 'uppercase',
        letterSpacing: '1px',
        marginBottom: '6px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span>Connections ({entries.length})</span>
        <div style={{ display: 'flex', gap: '8px' }}>
          {entries.length > 0 && (
            <button type="button" onClick={clearAll} style={{
              background: 'none', border: 'none', color: 'var(--neon-red)',
              fontFamily: 'var(--font-mono)', fontSize: '12px', cursor: 'pointer', textTransform: 'uppercase',
            }}>
              Clear all
            </button>
          )}
          <button type="button" onClick={handleAddRow} style={{
            background: 'none', border: 'none', color: 'var(--neon-cyan)',
            fontFamily: 'var(--font-mono)', fontSize: '12px', cursor: 'pointer', textTransform: 'uppercase',
          }}>
            + Add row
          </button>
        </div>
      </div>

      {entries.length > 0 ? (
        <div style={{
          maxHeight: '200px',
          overflowY: 'auto',
          border: '1px solid var(--border-color)',
          borderRadius: '4px',
        }}>
          {/* Table header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 30px 1fr 28px',
            gap: '6px',
            padding: '6px 8px',
            background: 'rgba(0, 212, 255, 0.05)',
            borderBottom: '1px solid var(--border-color)',
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--text-dim)',
            textTransform: 'uppercase',
            letterSpacing: '1px',
            position: 'sticky',
            top: 0,
          }}>
            <span>From</span>
            <span />
            <span>To</span>
            <span />
          </div>

          {entries.map(entry => {
            const isSelf = entry.from === entry.to;
            const isExisting = existingSet.has(`${entry.from}|${entry.to}`);
            return (
              <div
                key={entry.key}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 30px 1fr 28px',
                  gap: '6px',
                  padding: '4px 8px',
                  alignItems: 'center',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                  opacity: isSelf || isExisting ? 0.4 : 1,
                }}
              >
                <select
                  value={entry.from}
                  onChange={e => updateEntry(entry.key, 'from', e.target.value)}
                  style={inputStyle}
                >
                  {availableNodes.map(n => (
                    <option key={n.id} value={n.id}>{n.name}</option>
                  ))}
                </select>
                <span style={{
                  textAlign: 'center',
                  color: 'var(--neon-cyan)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '13px',
                }}>
                  →
                </span>
                <select
                  value={entry.to}
                  onChange={e => updateEntry(entry.key, 'to', e.target.value)}
                  style={inputStyle}
                >
                  {availableNodes.map(n => (
                    <option key={n.id} value={n.id}>{n.name}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => removeEntry(entry.key)}
                  style={{
                    background: 'none', border: 'none', color: 'var(--neon-red)',
                    cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '13px',
                    padding: '0', lineHeight: 1,
                  }}
                >
                  x
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <div style={{
          padding: '24px',
          textAlign: 'center',
          fontFamily: 'var(--font-mono)',
          fontSize: '13px',
          color: 'var(--text-dim)',
          border: '1px dashed var(--border-color)',
          borderRadius: '4px',
        }}>
          No connections yet. Use Quick Connect or Add Row above.
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
            fontSize: '13px',
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
            background: validCount > 0 ? 'rgba(0, 212, 255, 0.08)' : 'transparent',
            border: `1px solid ${validCount > 0 ? 'var(--neon-cyan)' : 'var(--border-color)'}`,
            borderRadius: '4px',
            color: validCount > 0 ? 'var(--neon-cyan)' : 'var(--text-dim)',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
            cursor: validCount > 0 ? 'pointer' : 'default',
            opacity: validCount > 0 ? 1 : 0.5,
          }}
        >
          Add {validCount > 0 ? `${validCount} Connection${validCount > 1 ? 's' : ''}` : 'Connections'}
        </button>
      </div>
    </div>
  );
}

export function BulkConnectionDialog({
  open,
  onClose,
  onSubmit,
  availableNodes,
  existingConnections,
}: BulkConnectionDialogProps) {
  return (
    <Dialog title="Bulk Add Connections" open={open} onClose={onClose} width={580}>
      {open && (
        <BulkConnectionDialogInner
          onClose={onClose}
          onSubmit={onSubmit}
          availableNodes={availableNodes}
          existingConnections={existingConnections}
        />
      )}
    </Dialog>
  );
}
