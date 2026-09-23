import { useState } from 'react';
import { CheckCircle2, Circle, CircleDashed, Loader2, Square, XCircle } from 'lucide-react';
import type { Job, JobStep } from '@/api/client';
import { cn } from '@/lib/cn';
import { useAppStore } from '@/store';
import { Button, Popover, PopoverContent, PopoverTrigger, Tabs, TabsList, TabsTrigger } from '@/ui';
import { JobLog } from '@/features/jobs/JobLog';
import { cancelJob } from '@/features/images/actions';

// Steps a deploy can still be cancelled in (the backend enforces the same).
const CANCELLABLE_STEPS = new Set(['validate', 'images']);

function duration(step: Pick<JobStep, 'started_at' | 'ended_at'>): string | null {
  if (!step.started_at) return null;
  const end = step.ended_at ? Date.parse(step.ended_at) : Date.now();
  const s = Math.max(0, Math.round((end - Date.parse(step.started_at)) / 1000));
  return s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
}

function StepIcon({ status }: { status: string }) {
  if (status === 'succeeded') return <CheckCircle2 className="text-success" />;
  if (status === 'failed') return <XCircle className="text-danger" />;
  if (status === 'cancelled') return <CircleDashed className="text-warning" />;
  if (status === 'running') return <Loader2 className="animate-spin text-info" />;
  return <Circle className="text-fg-subtle" />;
}

/** Wraps the deploy status badge: the running (or last) job's steps and logs, including image builds. */
export function JobDetailsPopover({ children }: { children: React.ReactElement }) {
  const open = useAppStore((s) => s.jobDetailsOpen);
  const setOpen = useAppStore((s) => s.setJobDetailsOpen);
  const job = useAppStore((s) => s.activeJob ?? s.lastJob);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent align="end" className="w-[min(560px,calc(100vw-32px))] p-0">
        {job ? <JobDetails key={job.id} job={job} /> : <p className="p-3 text-xs text-fg-muted">Nothing has been deployed from here yet.</p>}
      </PopoverContent>
    </Popover>
  );
}

function JobDetails({ job }: { job: Job }) {
  const report = useAppStore((s) => s.images);
  const [tab, setTab] = useState<string>(job.id);
  const builds = job.steps.find((s) => s.name === 'images')?.jobs ?? [];
  const running = job.status === 'queued' || job.status === 'running';
  const current = job.steps.find((s) => s.status === 'running');
  const cancellable = running && job.kind === 'deploy' && (!current || CANCELLABLE_STEPS.has(current.name));
  const buildName = (id: string) =>
    report?.images.find((i) => i.active_job?.id === id || i.last_job?.id === id)?.display_name ?? 'Image build';

  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <span className="text-xs font-semibold capitalize">{job.kind}</span>
        <span className={cn('text-2xs', job.status === 'failed' ? 'text-danger' : job.status === 'succeeded' ? 'text-success' : 'text-fg-muted')}>{job.status}</span>
        {cancellable ? (
          <Button size="xs" variant="ghost" className="ml-auto" onClick={() => void cancelJob(job.id, 'Deploy')}><Square /> Cancel</Button>
        ) : null}
      </div>
      <ol className="flex flex-col gap-1 px-3 py-2">
        {job.steps.map((s) => (
          <li key={s.name} className="flex items-start gap-2 text-xs [&_svg]:mt-0.5 [&_svg]:size-3.5 [&_svg]:shrink-0">
            <StepIcon status={s.status} />
            <span className="w-16 shrink-0 font-medium">{s.name}</span>
            <span className={cn('min-w-0 flex-1 break-words', s.status === 'failed' ? 'text-danger' : 'text-fg-muted')}>{s.message}</span>
            <span className="shrink-0 tabular text-2xs text-fg-subtle">{duration(s)}</span>
          </li>
        ))}
      </ol>
      {job.error ? <p className="mx-3 mb-2 rounded-md bg-danger-soft p-2 text-2xs text-danger">{job.error}</p> : null}
      <div className="border-t border-border px-3 pb-3 pt-2">
        {builds.length ? (
          <Tabs value={tab} onValueChange={setTab} className="mb-2">
            <TabsList variant="pills">
              <TabsTrigger value={job.id}>{job.kind === 'deploy' ? 'Deploy log' : 'Log'}</TabsTrigger>
              {builds.map((id) => <TabsTrigger key={id} value={id}>{buildName(id)}</TabsTrigger>)}
            </TabsList>
          </Tabs>
        ) : null}
        <JobLog key={tab} jobId={tab} className="h-56" />
      </div>
    </div>
  );
}
