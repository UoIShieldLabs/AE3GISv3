import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Dialog } from './ui/Dialog';
import { FormField } from './ui/FormField';
import { SelectField } from './ui/SelectField';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
import { generateId } from '../utils/idGenerator';
import { executePhase, executePhaseBatch, listAvailableScripts, listSessions, type PhaseExecutionResult, type AvailableScript, type ClassSessionRecord, type BatchTopologyResult } from '../api/client';
import type { TopologyData, Scenario, AttackPhase, ScriptExecution, Container } from '../data/sampleTopology';
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

interface ContainerWithContext {
  container: Container;
  siteName: string;
  subnetName: string;
  label: string;
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

  const onSaveRef = useRef(onSave);
  onSaveRef.current = onSave;
  const autoSaveTimer = useMemo(() => ({ id: null as ReturnType<typeof setTimeout> | null }), []);
  const scheduleAutoSave = useCallback(() => {
    if (autoSaveTimer.id) clearTimeout(autoSaveTimer.id);
    autoSaveTimer.id = setTimeout(() => { onSaveRef.current?.(); autoSaveTimer.id = null; }, 300);
  }, [autoSaveTimer]);

  const [availableScripts, setAvailableScripts] = useState<AvailableScript[]>([]);
  useEffect(() => {
    if (!open) return;
    listAvailableScripts()
      .then(res => setAvailableScripts(res.scripts))
      .catch(() => setAvailableScripts([]));
  }, [open]);

  // view: 'list' | 'scenario' | 'phase-edit'
  const [activeScenario, setActiveScenario] = useState<Scenario | null>(null);
  const [editingPhase, setEditingPhase] = useState<AttackPhase | null>(null);

  const [newScenarioName, setNewScenarioName] = useState('');
  const [newScenarioDesc, setNewScenarioDesc] = useState('');
  const [newPhaseName, setNewPhaseName] = useState('');
  const [newPhaseDesc, setNewPhaseDesc] = useState('');
  const [execContainerId, setExecContainerId] = useState('');
  const [execScript, setExecScript] = useState('');
  const [execArgs, setExecArgs] = useState('');

  const [executing, setExecuting] = useState(false);
  const [execResults, setExecResults] = useState<{ phaseId: string; results: PhaseExecutionResult[] } | null>(null);
  const [execError, setExecError] = useState('');

  const [sessions, setSessions] = useState<ClassSessionRecord[]>([]);
  const [batchSessionId, setBatchSessionId] = useState('');
  const [batchExecuting, setBatchExecuting] = useState(false);
  const [batchResults, setBatchResults] = useState<{ phaseId: string; results: BatchTopologyResult[] } | null>(null);
  const [batchError, setBatchError] = useState('');

  useEffect(() => {
    if (!open) return;
    listSessions().then(setSessions).catch(() => setSessions([]));
  }, [open]);

  const [deleteScenarioTarget, setDeleteScenarioTarget] = useState<Scenario | null>(null);
  const [deletePhaseTarget, setDeletePhaseTarget] = useState<AttackPhase | null>(null);

  const currentScenario = useMemo(
    () => activeScenario ? scenarios.find(s => s.id === activeScenario.id) || null : null,
    [scenarios, activeScenario],
  );
  const currentEditPhase = useMemo(
    () => currentScenario && editingPhase
      ? currentScenario.phases.find(p => p.id === editingPhase.id) || null
      : null,
    [currentScenario, editingPhase],
  );

  const handleCreateScenario = () => {
    if (!newScenarioName.trim()) return;
    const scenario: Scenario = { id: generateId(), name: newScenarioName.trim(), description: newScenarioDesc.trim() || undefined, phases: [] };
    dispatch({ type: 'ADD_SCENARIO', payload: scenario });
    scheduleAutoSave();
    setNewScenarioName('');
    setNewScenarioDesc('');
  };

  const handleDeleteScenario = () => {
    if (!deleteScenarioTarget) return;
    dispatch({ type: 'DELETE_SCENARIO', payload: { scenarioId: deleteScenarioTarget.id } });
    scheduleAutoSave();
    if (activeScenario?.id === deleteScenarioTarget.id) setActiveScenario(null);
    setDeleteScenarioTarget(null);
  };

  const handleCreatePhase = () => {
    if (!currentScenario || !newPhaseName.trim()) return;
    const phase: AttackPhase = { id: generateId(), name: newPhaseName.trim(), description: newPhaseDesc.trim() || undefined, executions: [] };
    dispatch({ type: 'ADD_PHASE', payload: { scenarioId: currentScenario.id, phase } });
    scheduleAutoSave();
    setNewPhaseName('');
    setNewPhaseDesc('');
  };

  const handleDeletePhase = () => {
    if (!deletePhaseTarget || !currentScenario) return;
    dispatch({ type: 'DELETE_PHASE', payload: { scenarioId: currentScenario.id, phaseId: deletePhaseTarget.id } });
    scheduleAutoSave();
    if (editingPhase?.id === deletePhaseTarget.id) setEditingPhase(null);
    setDeletePhaseTarget(null);
  };

  const handleAddExecution = () => {
    if (!currentScenario || !currentEditPhase || !execContainerId || !execScript.trim()) return;
    const newExecution: ScriptExecution = { containerId: execContainerId, script: execScript.trim(), args: execArgs.trim() ? execArgs.trim().split(/\s+/) : undefined };
    dispatch({ type: 'UPDATE_PHASE', payload: { scenarioId: currentScenario.id, phaseId: currentEditPhase.id, updates: { executions: [...currentEditPhase.executions, newExecution] } } });
    scheduleAutoSave();
    setExecScript('');
    setExecArgs('');
  };

  const handleRemoveExecution = (index: number) => {
    if (!currentScenario || !currentEditPhase) return;
    dispatch({ type: 'UPDATE_PHASE', payload: { scenarioId: currentScenario.id, phaseId: currentEditPhase.id, updates: { executions: currentEditPhase.executions.filter((_, i) => i !== index) } } });
    scheduleAutoSave();
  };

  const handleExecutePhase = useCallback(async (scenarioId: string, phaseId: string) => {
    if (!topologyId) return;
    setExecuting(true);
    setExecResults(null);
    setExecError('');
    try {
      const result = await executePhase(topologyId, scenarioId, phaseId);
      setExecResults({ phaseId, results: result.results });
    } catch (e) {
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
      setBatchResults({ phaseId, results: result.topology_results });
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

  // ── Phase edit view ───────────────────────────────────────────

  if (currentScenario && currentEditPhase) {
    return (
      <>
        <Dialog title="Edit Phase Scripts" open={open} onClose={onClose} width={700}>
          <button onClick={() => { setEditingPhase(null); }} style={{ ...btnCyan, marginBottom: '12px' }}>
            &larr; Back to {currentScenario.name}
          </button>

          <div style={{ fontFamily: 'var(--font-display)', color: '#ff00ff', fontSize: '20px', letterSpacing: '2px', textTransform: 'uppercase', marginBottom: '4px' }}>
            {currentEditPhase.name}
          </div>
          {currentEditPhase.description && (
            <div style={{ ...monoSmall, marginBottom: '12px' }}>{currentEditPhase.description}</div>
          )}

          <div style={sectionHeader}>Script Executions ({currentEditPhase.executions.length})</div>
          {currentEditPhase.executions.length === 0 ? (
            <div style={{ ...monoSmall, padding: '8px 0' }}>No scripts configured. Add one below.</div>
          ) : (
            currentEditPhase.executions.map((exec, i) => (
              <div key={i} style={rowStyle}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--text-primary)' }}>
                    {containerLabel(exec.containerId)}
                  </div>
                  <div style={{ ...monoSmall, fontSize: '12px' }}>
                    {exec.script}{exec.args?.length ? ` ${exec.args.join(' ')}` : ''}
                  </div>
                </div>
                <button onClick={() => handleRemoveExecution(i)} style={btnRed}>Del</button>
              </div>
            ))
          )}

          <div style={{ marginTop: '12px', padding: '12px', border: '1px solid var(--border-color)', borderRadius: '4px', background: 'rgba(20,20,30,0.3)' }}>
            <div style={{ ...sectionHeader, marginTop: 0 }}>Add Script Execution</div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div style={{ minWidth: '220px', flex: 1 }}>
                <SelectField
                  label="Target Container"
                  value={execContainerId}
                  onChange={(v) => { setExecContainerId(v); setExecScript(''); }}
                  options={[{ value: '', label: '— Select —' }, ...containersCtx.map(e => ({ value: e.container.id, label: e.label }))]}
                />
              </div>
              <div style={{ minWidth: '220px', flex: 1 }}>
                {(() => {
                  const selectedType = containersCtx.find(e => e.container.id === execContainerId)?.container.type;
                  const filtered = selectedType ? availableScripts.filter(s => s.containerTypes.includes(selectedType)) : availableScripts;
                  return filtered.length > 0 ? (
                    <SelectField
                      label="Script"
                      value={execScript}
                      onChange={setExecScript}
                      options={[{ value: '', label: '— Select —' }, ...filtered.map(s => ({ value: s.path, label: s.path }))]}
                    />
                  ) : (
                    <FormField label="Script Path" value={execScript} onChange={setExecScript} placeholder="/scripts/workstation/exploit.sh" />
                  );
                })()}
              </div>
              <div style={{ minWidth: '120px', flex: 1 }}>
                <FormField label="Args (optional)" value={execArgs} onChange={setExecArgs} placeholder="--target 10.0.1.5" />
              </div>
              <button onClick={handleAddExecution} disabled={!execContainerId || !execScript.trim()} style={{ ...btnGreen, marginBottom: '16px' }}>Add</button>
            </div>
          </div>
        </Dialog>
        <ConfirmDialog open={false} title="" message="" onConfirm={() => {}} onCancel={() => {}} />
      </>
    );
  }

  // ── Scenario detail: phases list with inline Run / Run Students ──

  if (currentScenario) {
    return (
      <>
        <Dialog title="Scenario" open={open} onClose={onClose} width={700}>
          <button onClick={() => { setActiveScenario(null); setExecResults(null); setExecError(''); setBatchResults(null); }} style={{ ...btnCyan, marginBottom: '12px' }}>
            &larr; Back to Scenarios
          </button>

          <div style={{ fontFamily: 'var(--font-display)', color: '#ff00ff', fontSize: '22px', letterSpacing: '2px', textTransform: 'uppercase', marginBottom: '4px' }}>
            {currentScenario.name}
          </div>
          {currentScenario.description && (
            <div style={{ ...monoSmall, marginBottom: '8px' }}>{currentScenario.description}</div>
          )}

          {/* Session selector — shown once at top if sessions exist */}
          {sessions.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '10px', marginBottom: '8px', padding: '10px 12px', border: '1px solid rgba(255,0,255,0.2)', borderRadius: '4px', background: 'rgba(255,0,255,0.03)' }}>
              <div style={{ flex: 1, maxWidth: '320px' }}>
                <SelectField
                  label="Deploy to class session"
                  value={batchSessionId}
                  onChange={setBatchSessionId}
                  options={[{ value: '', label: '— Select Session —' }, ...sessions.map(s => ({ value: s.id, label: s.name }))]}
                />
              </div>
              {batchSessionId && (
                <div style={{ ...monoSmall, paddingBottom: '18px', color: 'var(--neon-green)' }}>
                  "Run Students" buttons enabled
                </div>
              )}
            </div>
          )}

          {/* Phases */}
          <div style={sectionHeader}>Phases ({currentScenario.phases.length})</div>
          {currentScenario.phases.length === 0 ? (
            <div style={{ ...monoSmall, padding: '8px 0' }}>No phases defined. Create one below.</div>
          ) : (
            currentScenario.phases.map((phase, idx) => (
              <div key={phase.id}>
                <div style={rowStyle}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: '#ff00ff', width: '24px', textAlign: 'center', flexShrink: 0 }}>
                    {idx + 1}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '15px', color: 'var(--text-primary)', marginBottom: '2px' }}>
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
                    style={{ ...btnMagenta, opacity: (!isDeployed || phase.executions.length === 0) ? 0.4 : 1 }}
                    title={!isDeployed ? 'Deploy topology first' : 'Run on this topology'}
                  >
                    {executing && execResults?.phaseId !== phase.id ? '...' : 'Run'}
                  </button>
                  {sessions.length > 0 && (
                    <button
                      onClick={() => handleBatchExecute(currentScenario.id, phase.id)}
                      disabled={!batchSessionId || batchExecuting || phase.executions.length === 0}
                      style={{ ...btnAmber, opacity: (!batchSessionId || phase.executions.length === 0) ? 0.4 : 1 }}
                      title={!batchSessionId ? 'Select a class session above' : 'Run on all students in session'}
                    >
                      {batchExecuting && batchResults?.phaseId !== phase.id ? '...' : 'Run Students'}
                    </button>
                  )}
                  <button onClick={() => setEditingPhase(phase)} style={btnCyan}>Edit</button>
                  <button onClick={() => setDeletePhaseTarget(phase)} style={btnRed}>Del</button>
                </div>

                {/* Inline results for this phase */}
                {execResults?.phaseId === phase.id && (
                  <div style={{ marginBottom: '8px', marginTop: '-4px', padding: '10px 12px', border: '1px solid rgba(255,0,255,0.2)', borderRadius: '4px', background: 'rgba(255,0,255,0.03)', maxHeight: '180px', overflowY: 'auto' }}>
                    {execResults.results.map((r, i) => (
                      <div key={i} style={{ ...monoSmall, padding: '3px 0' }}>
                        <span style={{ color: r.returncode === 0 ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                          [{r.returncode === 0 ? 'OK' : `ERR:${r.returncode}`}]
                        </span>
                        {' '}{containerLabel(r.containerId)} — {r.script}
                        {r.stdout && <pre style={{ margin: '2px 0 0 16px', color: 'var(--text-dim)', fontSize: '12px', whiteSpace: 'pre-wrap' }}>{r.stdout.trim()}</pre>}
                        {r.stderr && <pre style={{ margin: '2px 0 0 16px', color: 'var(--neon-red)', fontSize: '12px', whiteSpace: 'pre-wrap' }}>{r.stderr.trim()}</pre>}
                      </div>
                    ))}
                  </div>
                )}

                {/* Inline batch results for this phase */}
                {batchResults?.phaseId === phase.id && (
                  <div style={{ marginBottom: '8px', marginTop: '-4px', padding: '10px 12px', border: '1px solid rgba(255,170,0,0.2)', borderRadius: '4px', background: 'rgba(255,170,0,0.03)', maxHeight: '180px', overflowY: 'auto' }}>
                    {batchResults.results.map((tr, i) => (
                      <div key={i} style={{ ...monoSmall, padding: '3px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                        <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{tr.label || tr.topology_id}</span>
                        {tr.skipped ? (
                          <span style={{ color: '#ffaa00', marginLeft: '8px' }}>Skipped ({tr.reason})</span>
                        ) : tr.exec_sessions ? (
                          <span style={{ color: 'var(--neon-purple, #b44dff)', marginLeft: '8px' }}>
                            {tr.exec_sessions.length} session{tr.exec_sessions.length !== 1 ? 's' : ''} pushed
                          </span>
                        ) : (
                          <span style={{ marginLeft: '8px' }}>
                            {(tr.results ?? []).map((r, j) => (
                              <span key={j} style={{ color: r.returncode === 0 ? 'var(--neon-green)' : 'var(--neon-red)', marginRight: '4px' }}>
                                [{r.returncode === 0 ? 'OK' : `ERR:${r.returncode}`}]
                              </span>
                            ))}
                          </span>
                        )}
                      </div>
                    ))}
                    <div style={{ ...monoSmall, marginTop: '6px', color: 'var(--text-dim)' }}>
                      {batchResults.results.filter(r => !r.skipped).length} pushed, {batchResults.results.filter(r => r.skipped).length} skipped
                    </div>
                  </div>
                )}
              </div>
            ))
          )}

          {execError && <div style={{ ...monoSmall, color: 'var(--neon-red)', marginTop: '8px' }}>{execError}</div>}
          {batchError && <div style={{ ...monoSmall, color: '#ffaa00', marginTop: '8px' }}>{batchError}</div>}

          {!isDeployed && (
            <div style={{ ...monoSmall, color: '#ffaa00', marginTop: '8px' }}>Topology must be deployed to run phases.</div>
          )}

          {/* Add phase form */}
          <div style={{ marginTop: '16px', padding: '12px', border: '1px solid var(--border-color)', borderRadius: '4px', background: 'rgba(20,20,30,0.3)' }}>
            <div style={{ ...sectionHeader, marginTop: 0 }}>Add Phase</div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
              <div style={{ flex: 1 }}>
                <FormField label="Phase Name" value={newPhaseName} onChange={setNewPhaseName} placeholder="e.g. Initial Access" />
              </div>
              <div style={{ flex: 1 }}>
                <FormField label="Description" value={newPhaseDesc} onChange={setNewPhaseDesc} placeholder="e.g. Phishing payload delivery" />
              </div>
              <button onClick={handleCreatePhase} disabled={!newPhaseName.trim()} style={{ ...btnGreen, marginBottom: '16px' }}>Add</button>
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

  // ── Scenarios list ────────────────────────────────────────────

  return (
    <>
      <Dialog title="Attack Scenarios" open={open} onClose={onClose} width={600}>
        <div style={sectionHeader}>Create Scenario</div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <FormField label="Scenario Name" value={newScenarioName} onChange={setNewScenarioName} placeholder="e.g. Ransomware Attack Chain" />
          </div>
          <div style={{ flex: 1 }}>
            <FormField label="Description" value={newScenarioDesc} onChange={setNewScenarioDesc} placeholder="Multi-phase attack simulation" />
          </div>
          <button onClick={handleCreateScenario} disabled={!newScenarioName.trim()} style={{ ...btnGreen, marginBottom: '16px' }}>Create</button>
        </div>

        <div style={sectionHeader}>Scenarios ({scenarios.length})</div>
        {scenarios.length === 0 ? (
          <div style={{ ...monoSmall, padding: '12px 0' }}>No scenarios defined. Create one above.</div>
        ) : (
          scenarios.map(scenario => (
            <div key={scenario.id} style={rowStyle}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '15px', color: 'var(--text-primary)', marginBottom: '2px' }}>
                  {scenario.name}
                </div>
                <div style={monoSmall}>
                  {scenario.phases.length} phase{scenario.phases.length !== 1 ? 's' : ''}
                  {scenario.description ? ` — ${scenario.description}` : ''}
                </div>
              </div>
              <button onClick={() => { setActiveScenario(scenario); setExecResults(null); setBatchResults(null); setExecError(''); setBatchError(''); }} style={btnAmber}>
                Open
              </button>
              <button onClick={() => setDeleteScenarioTarget(scenario)} style={btnRed}>Del</button>
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
