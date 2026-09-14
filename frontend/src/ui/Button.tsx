import { Slot } from 'radix-ui';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/cn';

export const buttonVariants = cva(
  [
    'inline-flex shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-md font-medium',
    'transition-colors duration-100 select-none',
    'disabled:pointer-events-none disabled:opacity-50',
    'focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-1',
    '[&_svg]:pointer-events-none [&_svg]:shrink-0',
  ],
  {
    variants: {
      variant: {
        primary: 'bg-accent text-accent-fg hover:bg-accent-hover shadow-sm',
        secondary: 'bg-surface-2 text-fg border border-border hover:bg-active',
        outline: 'border border-border-strong bg-transparent text-fg hover:bg-hover',
        ghost: 'bg-transparent text-fg-muted hover:bg-hover hover:text-fg',
        danger: 'bg-danger text-white hover:opacity-90 shadow-sm',
        'danger-soft': 'bg-danger-soft text-danger hover:bg-danger hover:text-white',
        link: 'text-accent underline-offset-4 hover:underline',
      },
      size: {
        xs: 'h-6 px-2 text-xs [&_svg]:size-3',
        sm: 'h-7 px-2.5 text-xs [&_svg]:size-3.5',
        md: 'h-8 px-3 text-[13px] [&_svg]:size-4',
        lg: 'h-9 px-4 text-sm [&_svg]:size-4',
        icon: 'size-8 [&_svg]:size-4',
        'icon-sm': 'size-7 [&_svg]:size-3.5',
        'icon-xs': 'size-6 [&_svg]:size-3.5',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
);

export interface ButtonProps
  extends React.ComponentProps<'button'>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export function Button({ className, variant, size, asChild, loading, disabled, children, ...props }: ButtonProps) {
  const Comp = asChild ? Slot.Root : 'button';
  return (
    <Comp
      type={asChild ? undefined : 'button'}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <Loader2 className="animate-spin" /> : null}
      {children}
    </Comp>
  );
}
