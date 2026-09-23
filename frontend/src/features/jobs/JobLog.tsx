import { useEffect, useRef } from 'react';
import { cn } from '@/lib/cn';
import { Spinner } from '@/ui';
import { useJobLog } from './useJobLog';

const STEP = /^(?:\[[\d:]+\] )?(?:#\d+ \[|── )/;

function lineClass(line: string): string {
  if (/\bERROR\b|error:|failed/i.test(line)) return 'text-danger';
  if (STEP.test(line)) return 'text-fg';
  return 'text-fg-muted';
}

/** A job's live log: follows new output, sticks to the bottom unless scrolled up. */
export function JobLog({ jobId, className, emptyText = 'No output yet.' }: { jobId: string | null | undefined; className?: string; emptyText?: string }) {
  const log = useJobLog(jobId);
  const ref = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  useEffect(() => {
    const el = ref.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [log.lines.length]);

  if (!jobId) return null;
  return (
    <div
      ref={ref}
      onScroll={(e) => {
        const el = e.currentTarget;
        stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
      }}
      className={cn('overflow-auto rounded-md border border-border bg-canvas p-2 font-mono text-2xs leading-4', className)}
      role="log"
      aria-live="polite"
    >
      {log.skippedBytes > 0 || log.droppedLines > 0 ? (
        <div className="mb-1 text-fg-subtle">… earlier output not shown</div>
      ) : null}
      {log.lines.length === 0 ? (
        <div className="flex items-center gap-2 text-fg-subtle">{!log.done ? <Spinner className="size-3" /> : null}{emptyText}</div>
      ) : (
        log.lines.map((line, i) => (
          <div key={i} className={cn('whitespace-pre-wrap break-all', lineClass(line))}>{line || ' '}</div>
        ))
      )}
      {!log.done && log.lines.length > 0 ? <Spinner className="mt-1 size-3 text-fg-subtle" /> : null}
    </div>
  );
}
