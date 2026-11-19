import { cn } from '@/lib/cn';

/** A titled group in a side nav (the Images sheet's sources, the library rail). */
export function NavGroup({ title, action, children, className }: {
  title: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-col gap-0.5', className)}>
      <div className="flex h-6 items-center justify-between px-2 text-2xs font-medium uppercase tracking-wide text-fg-subtle">
        {title}
        {action}
      </div>
      {children}
    </div>
  );
}

export interface NavItemProps extends React.ComponentProps<'button'> {
  icon?: React.ReactNode;
  label: React.ReactNode;
  count?: React.ReactNode;
  selected?: boolean;
  /** Before the count: a spinner, a warning dot. */
  adornment?: React.ReactNode;
  /** Nested under the item above. */
  inset?: boolean;
}

/** One entry of a side nav: icon, label, count; `aria-current` when selected. */
export function NavItem({ icon, label, count, selected, adornment, inset, className, ...props }: NavItemProps) {
  return (
    <button
      type="button"
      aria-current={selected ? 'true' : undefined}
      className={cn(
        'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-hover [&_svg]:size-3.5 [&_svg]:shrink-0 [&_svg]:text-fg-subtle',
        inset && 'pl-7',
        selected && 'bg-active',
        className,
      )}
      {...props}
    >
      {icon}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {adornment}
      {count !== undefined && count !== null ? <span className="tabular text-2xs text-fg-subtle">{count}</span> : null}
    </button>
  );
}
