import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Dialog } from './ui/Dialog';
import { FormField } from './ui/FormField';
import { SelectField } from './ui/SelectField';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
import { generateId } from '../utils/idGenerator';
import { executePhase, executePhaseBatch, listAvailableScripts, listSessions, type PhaseExecutionResult, type AvailableScript, type ClassSessionRecord, type BatchTopologyResult } from '../api/client';
import type { TopologyData, Scenario, AttackPhase, ScriptExecution, Container, ContainerType } from '../data/sampleTopology';
import type { TopologyAction } from '../store/topologyReducer';

interface ScenarioPanelProps {
  open: boolean;
  onClose: () => void;
  topology: TopologyData;
  topologyId: string | null;
  deployStatus: string;
  dispatch: React.Dispatch<TopologyAction>;
  onSave?: () => void;
}

// ── Shared inline styles (matching ClassroomPanel) ──────────────

const rowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '12px 16px',
  border: '1px solid var(--border-color)',
  borderRadius: '4px',
  background: 'rgba(20,20,30,0.5)',
  marginBottom: '8px',
};

const btnSmall = (color: string, bg: string): React.CSSProperties => ({
  padding: '8px 14px',
  background: bg,
  border: `1px solid ${color}`,
  color,
  fontFamily: 'var(--font-mono)',
  fontSize: '13px',
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
const btnMagenta = btnSmall('#ff00ff', 'rgba(255,0,255,0.08)');

const sectionHeader: React.CSSProperties = {
  fontFamily: 'var(--font-display)',
  color: 'var(--neon-cyan)',
  fontSize: '15px',
  letterSpacing: '1px',
  textTransform: 'uppercase',
  marginBottom: '10px',
  marginTop: '16px',
};

const monoSmall: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: '13px',
  color: 'var(--text-secondary)',
};

// ── Helper: collect all containers with site/subnet context ─────

interface ContainerWithContext {
  container: Container;
  siteName: string;
  subnetName: string;
  label: string; // "SiteName / SubnetName / ContainerName (type)"
}

function allContainersWithContext(topology: TopologyData): ContainerWithContext[] {
  const result: ContainerWithContext[] = [];
  for (const site of topology.sites) {
    for (const subnet of site.subnets) {
      for (const container of subnet.containers) {
        result.push({
          container,
          siteName: site.name,
          subnetName: subnet.name,
          label: `${site.name} / ${subnet.name} / ${container.name} (${container.type})`,
        });
      }
    }
  }
  return result;
}

/** Map from container type to which script directory gets mounted */
const SCRIPT_TYPE_MAP: Record<ContainerType, string> = {
  'workstation': 'workstation',
  'hmi': 'workstation',
  'web-server': 'server',
  'file-server': 'server',
  'plc': 'server',
  'router': 'router',
  'firewall': 'firewall',
  'switch': 'switch',
};

// ── Component ───────────────────────────────────────────────────

export function ScenarioPanel({
  open,
  onClose,
  topology,
  topologyId,
  deployStatus,
  dispatch,
  onSave,
}: ScenarioPanelProps) {
  const scenarios = topology.scenarios || [];
  const containersCtx = useMemo(() => allContainersWithContext(topology), [topology]);

  // Auto-save after scenario mutations (debounced to batch rapid changes)
  // Use a ref so the timeout always calls the latest onSave (avoids stale closure)
  const onSaveRef = useRef(onSave);
  onSaveRef.current = onSave;
  const autoSaveTimer = useMemo(() => ({ id: null as ReturnType<typeof setTimeout> | null }), []);
  const scheduleAutoSave = useCallback(() => {
    if (autoSaveTimer.id) clearTimeout(autoSaveTimer.id);
    autoSaveTimer.id = setTimeout(() => { onSaveRef.current?.(); autoSaveTimer.id = null; }, 300);
  }, [autoSaveTimer]);

  // ── Available scripts from backend
  const [availableScripts, setAvailableScripts] = useState<AvailableScript[]>([]);
  useEffect(() => {
    if (!open) return;
    listAvailableScripts()
      .then(res => { console.log('Available scripts:', res.scripts); setAvailableScripts(res.scripts); })
      .catch(err => { console.error('Failed to fetch scripts:', err); setAvailableScripts([]); });
  }, [open]);

  // ── View state
  const [activeScenario, setActiveScenario] = useState<Scenario | null>(null);
  const [activePhase, setActivePhase] = useState<AttackPhase | null>(null);

  // ── Create scenario form
  const [newScenarioName, setNewScenarioName] = useState('');
  const [newScenarioDesc, setNewScenarioDesc] = useState('');

  // ── Create phase form
  const [newPhaseName, setNewPhaseName] = useState('');
  const [newPhaseDesc, setNewPhaseDesc] = useState('');

  // ── Add execution form
  const [execContainerId, setExecContainerId] = useState('');
  const [execScript, setExecScript] = useState('');
  const [execArgs, setExecArgs] = useState('');

  // ── Execution results
  const [executing, setExecuting] = useState(false);
  const [execResults, setExecResults] = useState<PhaseExecutionResult[] | null>(null);
  const [execError, setExecError] = useState('');

  // ── Batch execution
  const [sessions, setSessions] = useState<ClassSessionRecord[]>([]);
  const [batchSessionId, setBatchSessionId] = useState('');
  const [batchExecuting, setBatchExecuting] = useState(false);
  const [batchResults, setBatchResults] = useState<BatchTopologyResult[] | null>(null);
  const [batchError, setBatchError] = useState('');

  // Fetch sessions when panel opens
  useEffect(() => {
    if (!open) return;
    listSessions()
      .then(setSessions)
      .catch(() => setSessions([]));
  }, [open]);

  // ── Delete confirmations
  const [deleteScenarioTarget, setDeleteScenarioTarget] = useState<Scenario | null>(null);
  const [deletePhaseTarget, setDeletePhaseTarget] = useState<AttackPhase | null>(null);

  // Keep active references in sync with topology state
  const currentScenario = useMemo(
    () => activeScenario ? scenarios.find(s => s.id === activeScenario.id) || null : null,
    [scenarios, activeScenario],
  );
  const currentPhase = useMemo(
    () => currentScenario && activePhase
      ? currentScenario.phases.find(p => p.id === activePhase.id) || null
      : null,
    [currentScenario, activePhase],
  );

  // ── Handlers ──────────────────────────────────────────────────

  const handleCreateScenario = () => {
    if (!newScenarioName.trim()) return;
    const scenario: Scenario = {
      id: generateId(),
      name: newScenarioName.trim(),
      description: newScenarioDesc.trim() || undefined,
      phases: [],
    };
    dispatch({ type: 'ADD_SCENARIO', payload: scenario });
    scheduleAutoSave();
    setNewScenarioName('');
    setNewScenarioDesc('');
  };

  const handleDeleteScenario = () => {
    if (!deleteScenarioTarget) return;
    dispatch({ type: 'DELETE_SCENARIO', payload: { scenarioId: deleteScenarioTarget.id } });
    scheduleAutoSave();
    if (activeScenario?.id === deleteScenarioTarget.id) {
      setActiveScenario(null);
      setActivePhase(null);
    }
    setDeleteScenarioTarget(null);
  };

  const handleCreatePhase = () => {
    if (!currentScenario || !newPhaseName.trim()) return;
    const phase: AttackPhase = {
      id: generateId(),
      name: newPhaseName.trim(),
      description: newPhaseDesc.trim() || undefined,
      executions: [],
    };
    dispatch({ type: 'ADD_PHASE', payload: { scenarioId: currentScenario.id, phase } });
    scheduleAutoSave();
    setNewPhaseName('');
    setNewPhaseDesc('');
  };

  const handleDeletePhase = () => {
    if (!deletePhaseTarget || !currentScenario) return;
    dispatch({
      type: 'DELETE_PHASE',
      payload: { scenarioId: currentScenario.id, phaseId: deletePhaseTarget.id },
    });
    scheduleAutoSave();
    if (activePhase?.id === deletePhaseTarget.id) setActivePhase(null);
    setDeletePhaseTarget(null);
  };

  const handleAddExecution = () => {
    if (!currentScenario || !currentPhase || !execContainerId || !execScript.trim()) return;
    const newExecution: ScriptExecution = {
      containerId: execContainerId,
      script: execScript.trim(),
      args: execArgs.trim() ? execArgs.trim().split(/\s+/) : undefined,
    };
    const updatedExecutions = [...currentPhase.executions, newExecution];
    dispatch({
      type: 'UPDATE_PHASE',
      payload: {
        scenarioId: currentScenario.id,
        phaseId: currentPhase.id,
        updates: { executions: updatedExecutions },
      },
    });
    scheduleAutoSave();
    setExecScript('');
    setExecArgs('');
  };

  const handleRemoveExecution = (index: number) => {
    if (!currentScenario || !currentPhase) return;
    const updatedExecutions = currentPhase.executions.filter((_, i) => i !== index);
    dispatch({
      type: 'UPDATE_PHASE',
      payload: {
        scenarioId: currentScenario.id,
        phaseId: currentPhase.id,
        updates: { executions: updatedExecutions },
      },
    });
    scheduleAutoSave();
  };

  const handleExecutePhase = useCallback(async (scenarioId: string, phaseId: string) => {
    if (!topologyId) return;
    setExecuting(true);
    setExecResults(null);
    setExecError('');
    try {
      const result = await executePhase(topologyId, scenarioId, phaseId);
      console.log('Phase execution result:', result);
      setExecResults(result.results);
    } catch (e) {
      console.error('Phase execution error:', e);
      setExecError(e instanceof Error ? e.message : 'Execution failed');
    } finally {
      setExecuting(false);
    }
  }, [topologyId]);

  const handleBatchExecute = useCallback(async (scenarioId: string, phaseId: string) => {
    if (!batchSessionId) return;
    setBatchExecuting(true);
    setBatchResults(null);
    setBatchError('');
    try {
      const result = await executePhaseBatch(batchSessionId, scenarioId, phaseId);
      setBatchResults(result.topology_results);
    } catch (e) {
      setBatchError(e instanceof Error ? e.message : 'Batch execution failed');
    } finally {
      setBatchExecuting(false);
    }
  }, [batchSessionId]);

  const containerLabel = (id: string) => {
    const entry = containersCtx.find(e => e.container.id === id);
    return entry ? `${entry.siteName} / ${entry.subnetName} / ${entry.container.name} (${entry.container.ip})` : id;
  };

  const isDeployed = deployStatus === 'deployed';

  // ── Render: Phase detail view ─────────────────────────────────

  if (currentScenario && currentPhase) {
    return (
      <>
        <Dialog title="Scenario — Phase" open={open} onClose={onClose} width={700}>
          <button
            onClick={() => { setActivePhase(null); setExecResults(null); setExecError(''); }}
            style={{ ...btnCyan, marginBottom: '12px' }}
          >
            &larr; Back to {currentScenario.name}
          </button>

          <div style={{
            fontFamily: 'var(--font-display)',
            color: '#ff00ff',
            fontSize: '20px',
            letterSpacing: '2px',
            textTransform: 'uppercase',
            marginBottom: '4px',
          }}>
            {currentPhase.name}
          </div>
          {currentPhase.description && (
            <div style={{ ...monoSmall, marginBottom: '12px' }}>{currentPhase.description}</div>
          )}

          {/* Execute button */}
          <div style={{ marginBottom: '16px' }}>
            <button
              onClick={() => handleExecutePhase(currentScenario.id, currentPhase.id)}
              disabled={executing || !isDeployed || currentPhase.executions.length === 0}
              style={{
                ...btnMagenta,
                padding: '10px 20px',
                fontSize: '14px',
                opacity: (!isDeployed || currentPhase.executions.length === 0) ? 0.4 : 1,
              }}
              title={!isDeployed ? 'Topology must be deployed' : ''}
            >
              {executing ? 'Executing...' : 'Execute Phase'}
            </button>
            {!isDeployed && (
              <span style={{ ...monoSmall, marginLeft: '12px', color: '#ffaa00' }}>
                Deploy topology first
              </span>
            )}
          </div>

          {/* Execution results */}
          {execError && (
            <div style={{ ...monoSmall, color: 'var(--neon-red)', marginBottom: '12px' }}>
              {execError}
            </div>
          )}
          {execResults && (
            <div style={{
              marginBottom: '16px',
              padding: '12px',
              border: '1px solid rgba(255,0,255,0.2)',
              borderRadius: '4px',
              background: 'rgba(255,0,255,0.03)',
              maxHeight: '200px',
              overflowY: 'auto',
            }}>
              <div style={{ ...sectionHeader, marginTop: 0 }}>Results</div>
              {execResults.map((r, i) => (
                <div key={i} style={{
                  ...monoSmall,
                  padding: '6px 0',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                }}>
                  <span style={{ color: r.returncode === 0 ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                    [{r.returncode === 0 ? 'OK' : `ERR:${r.returncode}`}]
                  </span>
                  {' '}{containerLabel(r.containerId)} — {r.script}
                  {r.stdout && <pre style={{ margin: '4px 0 0 16px', color: 'var(--text-dim)', fontSize: '12px', whiteSpace: 'pre-wrap' }}>{r.stdout.trim()}</pre>}
                  {r.stderr && <pre style={{ margin: '4px 0 0 16px', color: 'var(--neon-red)', fontSize: '12px', whiteSpace: 'pre-wrap' }}>{r.stderr.trim()}</pre>}
                </div>
              ))}
            </div>
          )}

          {/* Batch execute on all students */}
          {sessions.length > 0 && currentPhase.executions.length > 0 && (
            <div style={{
              marginBottom: '16px',
              padding: '12px',
              border: '1px solid rgba(255,0,255,0.2)',
              borderRadius: '4px',
              background: 'rgba(255,0,255,0.03)',
            }}>
              <div style={{ ...sectionHeader, marginTop: 0 }}>Execute on All Students</div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <SelectField
                    label="Class Session"
                    value={batchSessionId}
                    onChange={setBatchSessionId}
                    options={[
                      { value: '', label: '\u2014 Select Session \u2014' },
                      ...sessions.map(s => ({
                        value: s.id,
                        label: s.name,
                      })),
                    ]}
                  />
                </div>
                <button
                  onClick={() => handleBatchExecute(currentScenario.id, currentPhase.id)}
                  disabled={!batchSessionId || batchExecuting}
                  style={{
                    ...btnMagenta,
                    padding: '10px 20px',
                    fontSize: '14px',
                    marginBottom: '16px',
                    opacity: !batchSessionId ? 0.4 : 1,
                  }}
                >
                  {batchExecuting ? 'Executing...' : 'Run on All Students'}
                </button>
              </div>

              {batchError && (
                <div style={{ ...monoSmall, color: 'var(--neon-red)', marginTop: '8px' }}>
                  {batchError}
                </div>
              )}

              {batchResults && (
                <div style={{ maxHeight: '250px', overflowY: 'auto', marginTop: '8px' }}>
                  {batchResults.map((tr, i) => (
                    <div key={i} style={{
                      ...monoSmall,
                      padding: '6px 0',
                      borderBottom: '1px solid rgba(255,255,255,0.05)',
                    }}>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>
                        {tr.label || tr.topology_id}
                      </span>
                      {tr.skipped ? (
                        <span style={{ color: '#ffaa00', marginLeft: '8px' }}>
                          Skipped ({tr.reason})
                        </span>
                      ) : (
                        <span style={{ marginLeft: '8px' }}>
                          {tr.results.map((r, j) => (
                            <span key={j} style={{
                              color: r.returncode === 0 ? 'var(--neon-green)' : 'var(--neon-red)',
                              marginRight: '6px',
                            }}>
                              [{r.returncode === 0 ? 'OK' : `ERR:${r.returncode}`}]
                            </span>
                          ))}
                        </span>
                      )}
                    </div>
                  ))}
                  <div style={{ ...monoSmall, marginTop: '8px', color: 'var(--text-dim)' }}>
                    {batchResults.filter(r => !r.skipped).length} executed,{' '}
                    {batchResults.filter(r => r.skipped).length} skipped
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Script executions list */}
          <div style={sectionHeader}>
            Script Executions ({currentPhase.executions.length})
          </div>
          {currentPhase.executions.length === 0 ? (
            <div style={{ ...monoSmall, padding: '8px 0' }}>
              No scripts configured. Add one below.
            </div>
          ) : (
            currentPhase.executions.map((exec, i) => (
              <div key={i} style={rowStyle}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '14px',
                    color: 'var(--text-primary)',
                  }}>
                    {containerLabel(exec.containerId)}
                  </div>
                  <div style={{ ...monoSmall, fontSize: '12px' }}>
                    {exec.script}{exec.args?.length ? ` ${exec.args.join(' ')}` : ''}
                  </div>
                </div>
                <button onClick={() => handleRemoveExecution(i)} style={btnRed}>
                  Del
                </button>
              </div>
            ))
          )}

          {/* Add execution form */}
          <div style={{
            marginTop: '12px',
            padding: '12px',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            background: 'rgba(20,20,30,0.3)',
          }}>
            <div style={{ ...sectionHeader, marginTop: 0 }}>Add Script Execution</div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div style={{ minWidth: '220px', flex: 1 }}>
                <SelectField
                  label="Target Container"
                  value={execContainerId}
                  onChange={(v) => { setExecContainerId(v); setExecScript(''); }}
                  options={[
                    { value: '', label: '\u2014 Select \u2014' },
                    ...containersCtx.map(e => ({
                      value: e.container.id,
                      label: e.label,
                    })),
                  ]}
                />
              </div>
              <div style={{ minWidth: '220px', flex: 1 }}>
                {(() => {
                  const selectedEntry = containersCtx.find(e => e.container.id === execContainerId);
                  const selectedType = selectedEntry?.container.type;
                  const scriptDir = selectedType ? SCRIPT_TYPE_MAP[selectedType] : undefined;
                  const filteredScripts = scriptDir
                    ? availableScripts.filter(s => s.scriptDir === scriptDir)
                    : availableScripts;
                  const hasScripts = filteredScripts.length > 0;
                  return hasScripts ? (
                    <SelectField
                      label="Script"
                      value={execScript}
                      onChange={setExecScript}
                      options={[
                        { value: '', label: '\u2014 Select \u2014' },
                        ...filteredScripts.map(s => ({
                          value: s.path,
                          label: s.path,
                        })),
                      ]}
                    />
                  ) : (
                    <FormField
                      label="Script Path"
                      value={execScript}
                      onChange={setExecScript}
                      placeholder="/scripts/workstation/exploit.sh"
                    />
                  );
                })()}
              </div>
              <div style={{ minWidth: '120px', flex: 1 }}>
                <FormField
                  label="Args (optional)"
                  value={execArgs}
                  onChange={setExecArgs}
                  placeholder="--target 10.0.1.5"
                />
              </div>
              <button
                onClick={handleAddExecution}
                disabled={!execContainerId || !execScript.trim()}
                style={{ ...btnGreen, marginBottom: '16px' }}
              >
                Add
              </button>
            </div>
          </div>
        </Dialog>

        <ConfirmDialog
          open={false}
          title=""
          message=""
          onConfirm={() => {}}
          onCancel={() => {}}
        />
      </>
    );
  }

  // ── Render: Scenario detail (phases list) ─────────────────────

  if (currentScenario) {
    return (
      <>
        <Dialog title="Scenario" open={open} onClose={onClose} width={650}>
          <button
            onClick={() => { setActiveScenario(null); setExecResults(null); setExecError(''); }}
            style={{ ...btnCyan, marginBottom: '12px' }}
          >
            &larr; Back to Scenarios
          </button>

          <div style={{
            fontFamily: 'var(--font-display)',
            color: '#ff00ff',
            fontSize: '22px',
            letterSpacing: '2px',
            textTransform: 'uppercase',
            marginBottom: '4px',
          }}>
            {currentScenario.name}
          </div>
          {currentScenario.description && (
            <div style={{ ...monoSmall, marginBottom: '8px' }}>{currentScenario.description}</div>
          )}

          {/* Phases */}
          <div style={sectionHeader}>
            Phases ({currentScenario.phases.length})
          </div>
          {currentScenario.phases.length === 0 ? (
            <div style={{ ...monoSmall, padding: '8px 0' }}>
              No phases defined. Create one below.
            </div>
          ) : (
            currentScenario.phases.map((phase, idx) => (
              <div key={phase.id} style={rowStyle}>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '14px',
                  color: '#ff00ff',
                  width: '28px',
                  textAlign: 'center',
                  flexShrink: 0,
                }}>
                  {idx + 1}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '15px',
                    color: 'var(--text-primary)',
                    marginBottom: '2px',
                  }}>
                    {phase.name}
                  </div>
                  <div style={monoSmall}>
                    {phase.executions.length} script{phase.executions.length !== 1 ? 's' : ''}
                    {phase.description ? ` — ${phase.description}` : ''}
                  </div>
                </div>
                <button
                  onClick={() => handleExecutePhase(currentScenario.id, phase.id)}
                  disabled={executing || !isDeployed || phase.executions.length === 0}
                  style={{
                    ...btnMagenta,
                    opacity: (!isDeployed || phase.executions.length === 0) ? 0.4 : 1,
                  }}
                  title={!isDeployed ? 'Deploy topology first' : ''}
                >
                  {executing ? '...' : 'Run'}
                </button>
                <button
                  onClick={() => setActivePhase(phase)}
                  style={btnCyan}
                >
                  Edit
                </button>
                <button
                  onClick={() => setDeletePhaseTarget(phase)}
                  style={btnRed}
                >
                  Del
                </button>
              </div>
            ))
          )}

          {/* Execution results at scenario level */}
          {execError && (
            <div style={{ ...monoSmall, color: 'var(--neon-red)', marginTop: '8px' }}>
              {execError}
            </div>
          )}
          {execResults && (
            <div style={{
              marginTop: '12px',
              padding: '12px',
              border: '1px solid rgba(255,0,255,0.2)',
              borderRadius: '4px',
              background: 'rgba(255,0,255,0.03)',
              maxHeight: '200px',
              overflowY: 'auto',
            }}>
              <div style={{ ...sectionHeader, marginTop: 0 }}>Last Execution Results</div>
              {execResults.map((r, i) => (
                <div key={i} style={{ ...monoSmall, padding: '4px 0' }}>
                  <span style={{ color: r.returncode === 0 ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                    [{r.returncode === 0 ? 'OK' : `ERR:${r.returncode}`}]
                  </span>
                  {' '}{containerLabel(r.containerId)} — {r.script}
                </div>
              ))}
            </div>
          )}

          {/* Create phase form */}
          <div style={{
            marginTop: '16px',
            padding: '12px',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            background: 'rgba(20,20,30,0.3)',
          }}>
            <div style={{ ...sectionHeader, marginTop: 0 }}>Add Phase</div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
              <div style={{ flex: 1 }}>
                <FormField
                  label="Phase Name"
                  value={newPhaseName}
                  onChange={setNewPhaseName}
                  placeholder="e.g. Initial Access"
                />
              </div>
              <div style={{ flex: 1 }}>
                <FormField
                  label="Description"
                  value={newPhaseDesc}
                  onChange={setNewPhaseDesc}
                  placeholder="e.g. Phishing payload delivery"
                />
              </div>
              <button
                onClick={handleCreatePhase}
                disabled={!newPhaseName.trim()}
                style={{ ...btnGreen, marginBottom: '16px' }}
              >
                Add
              </button>
            </div>
          </div>
        </Dialog>

        <ConfirmDialog
          open={!!deletePhaseTarget}
          title="Delete Phase"
          message={`Delete phase "${deletePhaseTarget?.name}"? All script executions will be removed.`}
          onConfirm={handleDeletePhase}
          onCancel={() => setDeletePhaseTarget(null)}
        />
      </>
    );
  }

  // ── Render: Scenarios list ────────────────────────────────────

  return (
    <>
      <Dialog title="Attack Scenarios" open={open} onClose={onClose} width={600}>
        <div style={sectionHeader}>Create Scenario</div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <FormField
              label="Scenario Name"
              value={newScenarioName}
              onChange={setNewScenarioName}
              placeholder="e.g. Ransomware Attack Chain"
            />
          </div>
          <div style={{ flex: 1 }}>
            <FormField
              label="Description"
              value={newScenarioDesc}
              onChange={setNewScenarioDesc}
              placeholder="Multi-phase attack simulation"
            />
          </div>
          <button
            onClick={handleCreateScenario}
            disabled={!newScenarioName.trim()}
            style={{ ...btnGreen, marginBottom: '16px' }}
          >
            Create
          </button>
        </div>

        <div style={sectionHeader}>Scenarios ({scenarios.length})</div>
        {scenarios.length === 0 ? (
          <div style={{ ...monoSmall, padding: '12px 0' }}>
            No scenarios defined. Create one above to orchestrate attack phases.
          </div>
        ) : (
          scenarios.map(scenario => (
            <div key={scenario.id} style={rowStyle}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '15px',
                  color: 'var(--text-primary)',
                  marginBottom: '2px',
                }}>
                  {scenario.name}
                </div>
                <div style={monoSmall}>
                  {scenario.phases.length} phase{scenario.phases.length !== 1 ? 's' : ''}
                  {scenario.description ? ` — ${scenario.description}` : ''}
                </div>
              </div>
              <button onClick={() => setActiveScenario(scenario)} style={btnAmber}>
                Manage
              </button>
              <button onClick={() => setDeleteScenarioTarget(scenario)} style={btnRed}>
                Del
              </button>
            </div>
          ))
        )}
      </Dialog>

      <ConfirmDialog
        open={!!deleteScenarioTarget}
        title="Delete Scenario"
        message={`Delete scenario "${deleteScenarioTarget?.name}"? All phases and script configurations will be removed.`}
        onConfirm={handleDeleteScenario}
        onCancel={() => setDeleteScenarioTarget(null)}
      />
    </>
  );
}
