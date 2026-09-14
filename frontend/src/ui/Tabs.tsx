import { Tabs as R } from 'radix-ui';
import { cn } from '@/lib/cn';

export const Tabs = R.Root;
export const TabsContent = R.Content;

export interface TabsListProps extends React.ComponentProps<typeof R.List> {
  variant?: 'underline' | 'pills';
}

export function TabsList({ className, variant = 'underline', ...props }: TabsListProps) {
  return (
    <R.List
      data-variant={variant}
      className={cn(
        'group/tabs flex shrink-0 items-center',
        variant === 'underline' ? 'gap-1 border-b border-border px-1' : 'gap-0.5 rounded-lg bg-surface-2 p-0.5',
        className,
      )}
      {...props}
    />
  );
}

export function TabsTrigger({ className, ...props }: React.ComponentProps<typeof R.Trigger>) {
  return (
    <R.Trigger
      className={cn(
        'inline-flex h-8 items-center gap-1.5 whitespace-nowrap px-2 text-xs font-medium text-fg-muted transition-colors',
        'hover:text-fg disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-3.5',
        'focus-visible:outline-2 focus-visible:outline-ring focus-visible:-outline-offset-2',
        // underline
        'group-data-[variant=underline]/tabs:-mb-px group-data-[variant=underline]/tabs:border-b-2 group-data-[variant=underline]/tabs:border-transparent',
        'group-data-[variant=underline]/tabs:data-[state=active]:border-accent group-data-[variant=underline]/tabs:data-[state=active]:text-fg',
        // pills
        'group-data-[variant=pills]/tabs:h-7 group-data-[variant=pills]/tabs:rounded-md',
        'group-data-[variant=pills]/tabs:data-[state=active]:bg-surface group-data-[variant=pills]/tabs:data-[state=active]:text-fg group-data-[variant=pills]/tabs:data-[state=active]:shadow-sm',
        className,
      )}
      {...props}
    />
  );
}
