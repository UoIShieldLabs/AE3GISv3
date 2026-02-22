import { useCallback, useEffect, useState } from 'react';
import { Dialog } from './ui/Dialog';
import { FormField } from './ui/FormField';
import { SelectField } from './ui/SelectField';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
import {
  listTopologies,
  listSessions,
  createSession,
  deleteSession,
  instantiateSession,
  listSlots,
  deleteSlot,
  deployTopology,
  destroyTopology,
  getTopologyStatus,
  type TopologySummary,
  type ClassSessionRecord,
  type StudentSlotRecord,
} from '../api/client';

interface ClassroomPanelProps {
  open: boolean;
  onClose: () => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ── Shared inline styles ──────────────────────────────────────────

const rowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '10px 12px',
  border: '1px solid var(--border-color)',
  borderRadius: '4px',
  background: 'rgba(20,20,30,0.5)',
  marginBottom: '8px',
};

const btnSmall = (color: string, bg: string): React.CSSProperties => ({
  padding: '5px 10px',
  background: bg,
  border: `1px solid ${color}`,
  color,
  fontFamily: 'var(--font-mono)',
  fontSize: '10px',
  textTransform: 'uppercase',
  letterSpacing: '1px',
  borderRadius: '4px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
});

const btnCyan = btnSmall('var(--neon-cyan)', 'rgba(0,212,255,0.08)');
const btnGreen = btnSmall('var(--neon-green)', 'rgba(0,255,159,0.08)');
const btnRed = btnSmall('var(--neon-red)', 'rgba(255,51,68,0.1)');
const btnAmber = btnSmall('#ffaa00', 'rgba(255,170,0,0.08)');

const sectionHeader: React.CSSProperties = {
  fontFamily: 'var(--font-display)',
  color: 'var(--neon-cyan)',
  fontSize: '12px',
  letterSpacing: '1px',
  textTransform: 'uppercase',
  marginBottom: '12px',
  marginTop: '20px',
};

const monoSmall: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: '11px',
  color: 'var(--text-secondary)',
};

// ── Component ─────────────────────────────────────────────────────

export function ClassroomPanel({ open, onClose }: ClassroomPanelProps) {
  // ── Session list state
  const [sessions, setSessions] = useState<ClassSessionRecord[]>([]);
  const [topologies, setTopologies] = useState<TopologySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ── Create session form
  const [newName, setNewName] = useState('');
  const [newTemplateId, setNewTemplateId] = useState('');

  // ── Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<ClassSessionRecord | null>(null);

  // ── Detail view
  const [activeSession, setActiveSession] = useState<ClassSessionRecord | null>(null);
  const [slots, setSlots] = useState<StudentSlotRecord[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [slotStatuses, setSlotStatuses] = useState<Map<string, string>>(new Map());

  // ── Instantiate form
  const [instCount, setInstCount] = useState('5');
  const [instPrefix, setInstPrefix] = useState('Student');
  const [instBusy, setInstBusy] = useState(false);

  // ── Batch deploy
  const [batchBusy, setBatchBusy] = useState(false);
  const [batchProgress, setBatchProgress] = useState('');

  // ── Delete slot confirmation
  const [deleteSlotTarget, setDeleteSlotTarget] = useState<StudentSlotRecord | null>(null);

  // ── Load sessions + topologies when panel opens
  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError('');
    setActiveSession(null);
    Promise.all([listSessions(), listTopologies()])
      .then(([s, t]) => {
        setSessions(s);
        setTopologies(t);
        if (t.length > 0 && !newTemplateId) setNewTemplateId(t[0].id);
      })
      .catch(() => setError('Failed to load data'))
      .finally(() => setLoading(false));
  }, [open]);

  // ── Load slots when entering detail view
  const openSession = useCallback(async (session: ClassSessionRecord) => {
    setActiveSession(session);
    setSlotsLoading(true);
    try {
      const s = await listSlots(session.id);
      setSlots(s);
      // Fetch topology statuses for each slot
      const statusMap = new Map<string, string>();
      await Promise.all(
        s.map(async (slot) => {
          try {
            const st = await getTopologyStatus(slot.topology_id);
            statusMap.set(slot.topology_id, st.status);
          } catch {
            statusMap.set(slot.topology_id, 'unknown');
          }
        }),
      );
      setSlotStatuses(statusMap);
    } catch {
      setSlots([]);
    } finally {
      setSlotsLoading(false);
    }
  }, []);

  // ── Create session
  const handleCreate = async () => {
    if (!newName.trim() || !newTemplateId) return;
    setError('');
    try {
      const created = await createSession(newName.trim(), newTemplateId);
      setSessions((prev) => [...prev, created]);
      setNewName('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create session');
    }
  };

  // ── Delete session
  const handleDeleteSession = async () => {
    if (!deleteTarget) return;
    try {
      await deleteSession(deleteTarget.id);
      setSessions((prev) => prev.filter((s) => s.id !== deleteTarget.id));
      if (activeSession?.id === deleteTarget.id) setActiveSession(null);
    } catch {
      // ignore
    }
    setDeleteTarget(null);
  };

  // ── Instantiate students
  const handleInstantiate = async () => {
    if (!activeSession) return;
    const count = parseInt(instCount, 10);
    if (isNaN(count) || count < 1 || count > 200) return;
    setInstBusy(true);
    setError('');
    try {
      const newSlots = await instantiateSession(activeSession.id, count, instPrefix || 'Student');
      setSlots((prev) => [...prev, ...newSlots]);
      // Mark new slots as idle
      setSlotStatuses((prev) => {
        const next = new Map(prev);
        for (const s of newSlots) next.set(s.topology_id, 'idle');
        return next;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to instantiate');
    } finally {
      setInstBusy(false);
    }
  };

  // ── Delete slot
  const handleDeleteSlot = async () => {
    if (!deleteSlotTarget || !activeSession) return;
    try {
      await deleteSlot(activeSession.id, deleteSlotTarget.id);
      setSlots((prev) => prev.filter((s) => s.id !== deleteSlotTarget.id));
    } catch {
      // ignore
    }
    setDeleteSlotTarget(null);
  };

  // ── Copy join code
  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code).catch(() => {});
  };

  // ── Copy all codes
  const copyAllCodes = () => {
    const text = slots
      .map((s) => `${s.label || s.id}\t${s.join_code}`)
      .join('\n');
    navigator.clipboard.writeText(text).catch(() => {});
  };

  // ── Batch deploy all
  const handleBatchDeploy = async () => {
    if (!activeSession) return;
    setBatchBusy(true);
    setBatchProgress('');
    const topoIds = slots.map((s) => s.topology_id);
    let done = 0;
    for (const topoId of topoIds) {
      const status = slotStatuses.get(topoId);
      if (status === 'deployed') {
        done++;
        continue;
      }
      setBatchProgress(`Deploying ${done + 1} of ${topoIds.length}...`);
      try {
        await deployTopology(topoId);
        setSlotStatuses((prev) => {
          const next = new Map(prev);
          next.set(topoId, 'deployed');
          return next;
        });
      } catch {
        setSlotStatuses((prev) => {
          const next = new Map(prev);
          next.set(topoId, 'error');
          return next;
        });
      }
      done++;
    }
    setBatchProgress(`Done — ${done} topologies processed`);
    setBatchBusy(false);
  };

  // ── Batch destroy all
  const handleBatchDestroy = async () => {
    if (!activeSession) return;
    setBatchBusy(true);
    setBatchProgress('');
    const topoIds = slots.map((s) => s.topology_id);
    let done = 0;
    for (const topoId of topoIds) {
      const status = slotStatuses.get(topoId);
      if (status === 'idle' || status === 'unknown') {
        done++;
        continue;
      }
      setBatchProgress(`Destroying ${done + 1} of ${topoIds.length}...`);
      try {
        await destroyTopology(topoId);
        setSlotStatuses((prev) => {
          const next = new Map(prev);
          next.set(topoId, 'idle');
          return next;
        });
      } catch {
        setSlotStatuses((prev) => {
          const next = new Map(prev);
          next.set(topoId, 'error');
          return next;
        });
      }
      done++;
    }
    setBatchProgress(`Done — ${done} topologies processed`);
    setBatchBusy(false);
  };

  // ── Status badge color
  const statusColor = (status: string) => {
    switch (status) {
      case 'deployed': return 'var(--neon-green)';
      case 'error': return 'var(--neon-red)';
      case 'deploying':
      case 'destroying': return '#ffaa00';
      default: return 'var(--text-dim)';
    }
  };

  // ── Render ────────────────────────────────────────────────────────

  return (
    <>
      <Dialog title="Classroom" open={open} onClose={onClose} width={760}>
        {loading ? (
          <div style={{ ...monoSmall, padding: '20px', textAlign: 'center' }}>Loading...</div>
        ) : activeSession ? (
          /* ── Session Detail View ── */
          <div>
            <button
              onClick={() => setActiveSession(null)}
              style={{ ...btnCyan, marginBottom: '16px' }}
            >
              &larr; Back to Sessions
            </button>

            <div style={{
              fontFamily: 'var(--font-display)',
              color: 'var(--neon-cyan)',
              fontSize: '16px',
              letterSpacing: '2px',
              textTransform: 'uppercase',
              marginBottom: '4px',
            }}>
              {activeSession.name}
            </div>
            <div style={monoSmall}>
              Template: {topologies.find((t) => t.id === activeSession.template_id)?.name || activeSession.template_id.slice(0, 8)}
              &nbsp;&middot;&nbsp;Created {formatDate(activeSession.created_at)}
            </div>

            {/* Instantiate form */}
            <div style={sectionHeader}>Add Students</div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
              <div style={{ width: '80px' }}>
                <FormField
                  label="Count"
                  value={instCount}
                  onChange={setInstCount}
                  type="number"
                  placeholder="5"
                />
              </div>
              <div style={{ flex: 1 }}>
                <FormField
                  label="Label Prefix"
                  value={instPrefix}
                  onChange={setInstPrefix}
                  placeholder="Student"
                />
              </div>
              <button
                onClick={handleInstantiate}
                disabled={instBusy}
                style={{ ...btnGreen, marginBottom: '16px', padding: '8px 16px' }}
              >
                {instBusy ? 'Creating...' : 'Generate'}
              </button>
            </div>

            {/* Batch actions */}
            <div style={sectionHeader}>
              Student Slots ({slots.length})
            </div>
            {slots.length > 0 && (
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                <button onClick={copyAllCodes} style={btnCyan}>
                  Copy All Codes
                </button>
                <button
                  onClick={handleBatchDeploy}
                  disabled={batchBusy}
                  style={btnGreen}
                >
                  Deploy All
                </button>
                <button
                  onClick={handleBatchDestroy}
                  disabled={batchBusy}
                  style={btnAmber}
                >
                  Destroy All
                </button>
                {batchProgress && (
                  <span style={{ ...monoSmall, alignSelf: 'center' }}>{batchProgress}</span>
                )}
              </div>
            )}

            {/* Slots list */}
            {slotsLoading ? (
              <div style={{ ...monoSmall, padding: '12px' }}>Loading slots...</div>
            ) : slots.length === 0 ? (
              <div style={{ ...monoSmall, padding: '12px' }}>
                No students yet. Use the form above to generate student slots.
              </div>
            ) : (
              <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
                {slots.map((slot) => {
                  const status = slotStatuses.get(slot.topology_id) || 'idle';
                  return (
                    <div key={slot.id} style={rowStyle}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '12px',
                          color: 'var(--text-primary)',
                          marginBottom: '2px',
                        }}>
                          {slot.label || 'Unnamed'}
                        </div>
                        <div style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '11px',
                          color: 'var(--text-dim)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}>
                          {slot.join_code}
                        </div>
                      </div>
                      <span style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '10px',
                        textTransform: 'uppercase',
                        letterSpacing: '1px',
                        color: statusColor(status),
                        whiteSpace: 'nowrap',
                      }}>
                        {status}
                      </span>
                      <button onClick={() => copyCode(slot.join_code)} style={btnCyan}>
                        Copy
                      </button>
                      <button onClick={() => setDeleteSlotTarget(slot)} style={btnRed}>
                        Del
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {error && (
              <div style={{ ...monoSmall, color: 'var(--neon-red)', marginTop: '8px' }}>{error}</div>
            )}
          </div>
        ) : (
          /* ── Session List View ── */
          <div>
            {/* Create session form */}
            <div style={sectionHeader}>Create Session</div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
              <div style={{ flex: 1 }}>
                <FormField
                  label="Session Name"
                  value={newName}
                  onChange={setNewName}
                  placeholder="e.g. Lab 1 - Firewall Config"
                />
              </div>
              <div style={{ flex: 1 }}>
                <SelectField
                  label="Template Topology"
                  value={newTemplateId}
                  onChange={setNewTemplateId}
                  options={topologies.map((t) => ({ value: t.id, label: t.name }))}
                />
              </div>
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || !newTemplateId}
                style={{ ...btnGreen, marginBottom: '16px', padding: '8px 16px' }}
              >
                Create
              </button>
            </div>

            {/* Sessions list */}
            <div style={sectionHeader}>Sessions ({sessions.length})</div>
            {sessions.length === 0 ? (
              <div style={{ ...monoSmall, padding: '12px' }}>
                No class sessions yet. Create one above.
              </div>
            ) : (
              sessions.map((session) => (
                <div key={session.id} style={rowStyle}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      color: 'var(--text-primary)',
                      marginBottom: '2px',
                    }}>
                      {session.name}
                    </div>
                    <div style={monoSmall}>
                      Template: {topologies.find((t) => t.id === session.template_id)?.name || session.template_id.slice(0, 8)}
                      &nbsp;&middot;&nbsp;{formatDate(session.created_at)}
                    </div>
                  </div>
                  <button onClick={() => openSession(session)} style={btnCyan}>
                    Manage
                  </button>
                  <button onClick={() => setDeleteTarget(session)} style={btnRed}>
                    Del
                  </button>
                </div>
              ))
            )}

            {error && (
              <div style={{ ...monoSmall, color: 'var(--neon-red)', marginTop: '8px' }}>{error}</div>
            )}
          </div>
        )}
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Session"
        message={`Delete "${deleteTarget?.name}"? All student slots and their topologies will be removed.`}
        onConfirm={handleDeleteSession}
        onCancel={() => setDeleteTarget(null)}
      />

      <ConfirmDialog
        open={!!deleteSlotTarget}
        title="Delete Student Slot"
        message={`Delete slot "${deleteSlotTarget?.label || deleteSlotTarget?.id}"? The student's topology will be removed.`}
        onConfirm={handleDeleteSlot}
        onCancel={() => setDeleteSlotTarget(null)}
      />
    </>
  );
}
