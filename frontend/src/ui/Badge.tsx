import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/cn';

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full border px-1.5 py-px text-2xs font-medium leading-4 whitespace-nowrap',
  {
    variants: {
      tone: {
        neutral: 'border-border bg-surface-2 text-fg-muted',
        accent: 'border-transparent bg-accent-soft text-accent',
        success: 'border-transparent bg-success-soft text-success',
        warning: 'border-transparent bg-warning-soft text-warning',
        danger: 'border-transparent bg-danger-soft text-danger',
        info: 'border-transparent bg-info-soft text-info',
        outline: 'border-border-strong bg-transparent text-fg-muted',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
);

export interface BadgeProps extends React.ComponentProps<'span'>, VariantProps<typeof badgeVariants> {
  /** Render a status dot before the label; `pulse` animates it. */
  dot?: boolean | 'pulse';
  /** Override the dot color (defaults to currentColor). */
  dotColor?: string;
  mono?: boolean;
}

export function Badge({ className, tone, dot, dotColor, mono, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ tone }), mono && 'font-mono', className)} {...props}>
      {dot ? (
        <span
          className={cn('size-1.5 rounded-full bg-current', dot === 'pulse' && 'animate-pulse')}
          style={dotColor ? { backgroundColor: dotColor } : undefined}
        />
      ) : null}
      {children}
    </span>
  );
}
