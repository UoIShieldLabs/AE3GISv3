import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/cn';

export function Section({ title, children, defaultOpen = true, action, className }: { title: string; children: React.ReactNode; defaultOpen?: boolean; action?: React.ReactNode; className?: string }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={cn('border-b border-border', className)}>
      <div className="flex items-center gap-1 px-3 py-2">
        <button type="button" onClick={() => setOpen((o) => !o)} className="flex flex-1 items-center gap-1 text-2xs font-semibold uppercase tracking-wide text-fg-subtle hover:text-fg">
          {open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
          {title}
        </button>
        {action}
      </div>
      {open ? <div className="flex flex-col gap-3 px-3 pb-3">{children}</div> : null}
    </section>
  );
}

export function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 text-xs">
      <span className="text-fg-muted">{label}</span>
      <span className="truncate font-medium tabular">{value}</span>
    </div>
  );
}

export function Row({ label, children, hint }: { label: string; children: React.ReactNode; hint?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-fg-muted">{label}</span>
      {children}
      {hint ? <span className="text-2xs text-fg-subtle">{hint}</span> : null}
    </div>
  );
}
