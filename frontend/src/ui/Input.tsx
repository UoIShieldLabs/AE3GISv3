import { cn } from '@/lib/cn';

export const inputClassName = cn(
  'flex h-8 w-full min-w-0 rounded-md border border-border bg-surface px-2.5 text-[13px] text-fg shadow-none',
  'placeholder:text-fg-subtle transition-colors',
  'hover:border-border-strong focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25',
  'disabled:cursor-not-allowed disabled:opacity-50',
  'aria-invalid:border-danger aria-invalid:focus:ring-danger/25',
);

export interface InputProps extends React.ComponentProps<'input'> {
  mono?: boolean;
  /** Element rendered inside the field on the left (icon) or right (button). */
  leading?: React.ReactNode;
  trailing?: React.ReactNode;
}

export function Input({ className, mono, leading, trailing, ...props }: InputProps) {
  if (!leading && !trailing) {
    return <input className={cn(inputClassName, mono && 'font-mono text-xs', className)} {...props} />;
  }
  return (
    <div className="relative flex items-center">
      {leading ? <span className="pointer-events-none absolute left-2.5 text-fg-subtle [&_svg]:size-3.5">{leading}</span> : null}
      <input
        className={cn(inputClassName, mono && 'font-mono text-xs', leading && 'pl-8', trailing && 'pr-8', className)}
        {...props}
      />
      {trailing ? <span className="absolute right-1.5 flex items-center">{trailing}</span> : null}
    </div>
  );
}

export function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      className={cn(inputClassName, 'h-auto min-h-16 resize-y py-2 leading-snug', className)}
      {...props}
    />
  );
}
