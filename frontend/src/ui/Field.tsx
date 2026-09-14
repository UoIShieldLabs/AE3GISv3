import { useId } from 'react';
import { Label as RLabel } from 'radix-ui';
import { cn } from '@/lib/cn';

export interface FieldProps {
  label: React.ReactNode;
  /** The control. Receives `id` and `aria-*` via cloneElement-free render prop. */
  children: (ctl: { id: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }) => React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  required?: boolean;
  inline?: boolean;
  className?: string;
  /** Extra content on the label row (e.g. a small action). */
  labelAction?: React.ReactNode;
}

/** Label + control + hint/error, with the ARIA wiring handled. */
export function Field({ label, children, hint, error, required, inline, className, labelAction }: FieldProps) {
  const id = useId();
  const descId = `${id}-desc`;
  const describedBy = error || hint ? descId : undefined;
  return (
    <div className={cn('flex gap-1', inline ? 'flex-row items-center justify-between' : 'flex-col', className)}>
      <div className="flex items-center justify-between gap-2">
        <RLabel.Root htmlFor={id} className="text-xs font-medium text-fg-muted">
          {label}
          {required ? <span className="ml-0.5 text-danger">*</span> : null}
        </RLabel.Root>
        {labelAction}
      </div>
      <div className={cn(inline && 'shrink-0')}>
        {children({ id, 'aria-invalid': error ? true : undefined, 'aria-describedby': describedBy })}
      </div>
      {error ? (
        <div id={descId} className="text-xs text-danger">{error}</div>
      ) : hint ? (
        <div id={descId} className="text-xs text-fg-subtle">{hint}</div>
      ) : null}
    </div>
  );
}
