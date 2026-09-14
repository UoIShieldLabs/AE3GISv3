import { cn } from '@/lib/cn';

export function Kbd({ className, ...props }: React.ComponentProps<'kbd'>) {
  return (
    <kbd
      className={cn(
        'inline-flex h-5 min-w-5 items-center justify-center rounded border border-border bg-surface-2 px-1 font-mono text-2xs text-fg-muted',
        className,
      )}
      {...props}
    />
  );
}
