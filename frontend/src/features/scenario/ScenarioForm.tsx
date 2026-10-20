import { useMemo } from 'react';
import { ChevronDown, ChevronUp, ListChecks, Play, Plus, Trash2 } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import type { AttackPhase, Scenario, ScriptExecution, TopologyData } from '@/types/topology';
import { nodesOf } from '@/features/monitor/selection';
import { Button, EmptyState, IconButton, Select } from '@/ui';
import { CommitInput } from '@/shell/inspector/CommitInput';
import { startScenarioPhase, startScenarioStep } from './actions';

// Stable fallback: a fresh `[]` inside the selector would change identity on
// every store read and make the shallow-equal subscription loop forever.
const NO_SCENARIOS: Scenario[] = [];

/** Author scenarios (phases → steps) and run a step or a whole phase.
 *  Scenarios are part of the saved topology, so running needs a deployed lab
 *  with no unsaved edits (the backend runs from what was deployed). */
export function ScenarioForm() {
  const { stored, deployStatus, dirty, backendId } = useAppShallow((s) => ({
    stored: (s.topology as TopologyData).scenarios,
    deployStatus: s.deployStatus,
    dirty: s.dirty,
    backendId: s.backendId,
  }));
  const scenarios = stored ?? NO_SCENARIOS;
  const topology = useAppStore((s) => s.topology);
  const nodeOptions = useMemo(
    () => nodesOf(topology).map((n) => ({ value: n.id, label: n.ip ? `${n.name} · ${n.ip}` : n.name })),
    [topology],
  );

  const canRun = deployStatus === 'deployed' && !dirty && !!backendId;
  const runHint = !backendId
    ? 'Save the topology first'
    : deployStatus !== 'deployed'
      ? 'Deploy the topology first'
      : dirty
        ? 'Save your changes first'
        : undefined;

  const a = () => useAppStore.getState();

  if (scenarios.length === 0) {
    return (
      <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
        <Header onAdd={() => a().addScenario()} />
        <EmptyState
          className="flex-1"
          icon={<ListChecks />}
          title="No scenarios yet"
          description="A scenario is phases of steps — each step an ordinary command run on a node. Add one, then step through it on a deployed lab."
          action={<Button size="sm" onClick={() => a().addScenario()}><Plus /> New scenario</Button>}
        />
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
      <Header onAdd={() => a().addScenario()} />
      <div className="min-h-0 flex-1 space-y-4 overflow-auto p-3">
        {runHint ? <p className="text-2xs text-fg-subtle">{runHint} to run steps.</p> : null}
        {scenarios.map((scenario) => (
          <ScenarioBlock
            key={scenario.id}
            scenario={scenario}
            nodeOptions={nodeOptions}
            canRun={canRun}
            runHint={runHint}
          />
        ))}
      </div>
    </div>
  );
}

function Header({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex items-center gap-2 border-b border-border px-3 py-2">
      <ListChecks className="size-4 text-fg-muted" aria-hidden />
      <span className="text-xs font-medium text-fg">Scenarios</span>
      <Button size="sm" variant="ghost" className="ml-auto" onClick={onAdd}><Plus /> New scenario</Button>
    </div>
  );
}

function ScenarioBlock({
  scenario, nodeOptions, canRun, runHint,
}: {
  scenario: Scenario;
  nodeOptions: { value: string; label: string }[];
  canRun: boolean;
  runHint?: string;
}) {
  const a = () => useAppStore.getState();
  return (
    <section className="rounded-md border border-border">
      <header className="flex items-center gap-2 border-b border-border bg-surface-2/50 px-2 py-1.5">
        <div className="min-w-0 flex-1">
          <CommitInput
            className="h-7 font-medium"
            value={scenario.name}
            onCommit={(name) => a().updateScenario(scenario.id, { name })}
            aria-label="Scenario name"
          />
        </div>
        <Button size="sm" variant="ghost" onClick={() => a().addPhase(scenario.id)}><Plus /> Phase</Button>
        <IconButton label="Remove scenario" size="icon-sm" onClick={() => a().removeScenario(scenario.id)}><Trash2 /></IconButton>
      </header>
      <div className="space-y-2 p-2">
        {(scenario.phases ?? []).length === 0 ? (
          <p className="px-1 text-2xs text-fg-subtle">No phases yet.</p>
        ) : (
          scenario.phases.map((phase) => (
            <PhaseBlock key={phase.id} phase={phase} nodeOptions={nodeOptions} canRun={canRun} runHint={runHint} />
          ))
        )}
      </div>
    </section>
  );
}

function PhaseBlock({
  phase, nodeOptions, canRun, runHint,
}: {
  phase: AttackPhase;
  nodeOptions: { value: string; label: string }[];
  canRun: boolean;
  runHint?: string;
}) {
  const a = () => useAppStore.getState();
  const steps = phase.executions ?? [];
  const defaultNode = nodeOptions[0]?.value ?? '';
  return (
    <div className="rounded-md border border-border bg-surface">
      <header className="flex items-center gap-2 px-2 py-1.5">
        <div className="min-w-0 flex-1">
          <CommitInput
            className="h-7"
            value={phase.name}
            onCommit={(name) => a().updatePhase(phase.id, { name })}
            aria-label="Phase name"
          />
        </div>
        <Button
          size="sm"
          variant="secondary"
          disabled={!canRun || steps.length === 0}
          title={runHint ?? (steps.length === 0 ? 'Add a step first' : 'Run every step in order')}
          onClick={() => void startScenarioPhase(phase.id, phase.name)}
        >
          <Play /> Run phase
        </Button>
        <IconButton label="Remove phase" size="icon-sm" onClick={() => a().removePhase(phase.id)}><Trash2 /></IconButton>
      </header>
      <ol className="divide-y divide-border border-t border-border">
        {steps.map((step, i) => (
          <StepRow
            key={i}
            step={step}
            index={i}
            count={steps.length}
            phaseId={phase.id}
            nodeOptions={nodeOptions}
            canRun={canRun}
            runHint={runHint}
          />
        ))}
      </ol>
      <div className="px-2 py-1.5">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => a().addStep(phase.id, { containerId: defaultNode, script: '' })}
        >
          <Plus /> Add step
        </Button>
      </div>
    </div>
  );
}

function StepRow({
  step, index, count, phaseId, nodeOptions, canRun, runHint,
}: {
  step: ScriptExecution;
  index: number;
  count: number;
  phaseId: string;
  nodeOptions: { value: string; label: string }[];
  canRun: boolean;
  runHint?: string;
}) {
  const a = () => useAppStore.getState();
  const runnable = canRun && !!step.containerId && !!step.script.trim();
  return (
    <li className="flex items-center gap-1.5 px-2 py-1.5">
      <span className="w-4 shrink-0 text-right font-mono text-2xs text-fg-subtle">{index + 1}</span>
      <Select
        size="sm"
        className="w-40 shrink-0"
        value={step.containerId}
        onValueChange={(containerId) => a().updateStep(phaseId, index, { containerId })}
        options={nodeOptions}
        placeholder="node"
        aria-label="Node"
      />
      <div className="min-w-0 flex-1">
        <CommitInput
          className="h-7 font-mono text-xs"
          value={step.script}
          onCommit={(script) => a().updateStep(phaseId, index, { script })}
          placeholder="command, e.g. ip -o addr"
          aria-label="Command"
        />
      </div>
      <IconButton label="Run step" size="icon-sm" disabled={!runnable} tooltip={runHint ?? 'Run this step'}
        onClick={() => void startScenarioStep({ containerId: step.containerId, script: step.script, args: step.args, label: '' })}>
        <Play />
      </IconButton>
      <IconButton label="Move up" size="icon-sm" disabled={index === 0} onClick={() => a().moveStep(phaseId, index, index - 1)}><ChevronUp /></IconButton>
      <IconButton label="Move down" size="icon-sm" disabled={index === count - 1} onClick={() => a().moveStep(phaseId, index, index + 1)}><ChevronDown /></IconButton>
      <IconButton label="Remove step" size="icon-sm" onClick={() => a().removeStep(phaseId, index)}><Trash2 /></IconButton>
    </li>
  );
}
