import { Download, ListChecks, Square } from 'lucide-react';
import { useAppStore } from '@/store';
import { locate } from '@/lib/topology';
import { Badge, Button } from '@/ui';
import { useScenarioStream, type StepView } from './useScenarioStream';
import { exportScenarioRun, openScenarioPanel, stopScenarioRun } from './actions';

type Tone = 'success' | 'danger' | 'warning' | 'neutral' | 'info';
const STATUS: Record<string, { label: string; tone: Tone }> = {
  running: { label: 'running', tone: 'info' },
  ok: { label: 'exit 0', tone: 'success' },
  failed: { label: 'failed', tone: 'danger' },
  timeout: { label: 'timed out', tone: 'warning' },
  error: { label: 'error', tone: 'danger' },
  stopped: { label: 'stopped', tone: 'neutral' },
};

function StepCard({ step, nameFor }: { step: StepView; nameFor: (id: string) => string }) {
  const s = STATUS[step.status] ?? { label: step.status, tone: 'neutral' as const };
  const code = step.status === 'failed' && step.exit_code !== null ? `exit ${step.exit_code}` : s.label;
  return (
    <section className="rounded-md border border-border bg-surface">
      <header className="flex items-center gap-2 border-b border-border px-3 py-1.5 text-xs">
        <span className="font-mono text-fg-subtle">{step.index + 1}</span>
        <span className="font-medium text-fg">{nameFor(step.container_id) || step.container_id}</span>
        <code className="min-w-0 flex-1 truncate font-mono text-fg-muted" title={step.command}>$ {step.command}</code>
        <Badge tone={s.tone} className="shrink-0">{code}</Badge>
      </header>
      {step.stdout || step.stderr ? (
        <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words px-3 py-2 font-mono text-2xs leading-relaxed text-fg">
          {step.stdout}
          {step.stderr ? <span className="text-danger">{step.stderr}</span> : null}
        </pre>
      ) : (
        <p className="px-3 py-2 text-2xs text-fg-subtle">{step.status === 'running' ? 'Running…' : 'No output'}</p>
      )}
    </section>
  );
}

/** A scenario run in the dock: each step's command and streamed output. */
export function ScenarioRunView({ jobId }: { jobId: string }) {
  const backendId = useAppStore((s) => s.backendId);
  const topology = useAppStore((s) => s.topology);
  const { run, steps, ended } = useScenarioStream(backendId, jobId);
  const live = run ? run.live : !ended;
  const nameFor = (id: string) => {
    const hit = locate(topology, id);
    return hit?.kind === 'container' ? hit.container.name : '';
  };
  const result = run?.result as { stopped_by?: string; ran?: number; failed?: number } | undefined;

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col text-sm">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2 text-xs">
        <ListChecks className="size-4 text-fg-muted" aria-hidden />
        <span className="font-medium text-fg">{run?.label || 'Scenario run'}</span>
        <span className="text-fg-subtle">
          {run ? `${run.step_count} step${run.step_count === 1 ? '' : 's'}` : ''}
          {result?.failed ? ` · ${result.failed} failed` : ''}
          {result?.stopped_by === 'user' || result?.stopped_by === 'destroy' ? ' · stopped' : ''}
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          {!live && run ? <Button size="sm" variant="ghost" onClick={() => exportScenarioRun(jobId)}><Download /> Export</Button> : null}
          {!live && run ? <Button size="sm" variant="ghost" onClick={() => openScenarioPanel()}><ListChecks /> Scenarios</Button> : null}
          {live ? <Button size="sm" variant="danger-soft" onClick={() => void stopScenarioRun(jobId)}><Square /> Stop</Button> : null}
        </div>
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-auto p-3">
        {run?.job.error ? <div className="rounded-md bg-danger-soft px-3 py-2 text-xs text-danger">{run.job.error}</div> : null}
        {steps.length === 0 ? <p className="text-xs text-fg-subtle">Waiting for the first step…</p> : null}
        {steps.map((step) => <StepCard key={step.index} step={step} nameFor={nameFor} />)}
      </div>
    </div>
  );
}
