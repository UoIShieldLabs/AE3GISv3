import { cn } from '@/lib/cn';

export interface EmptyStateProps extends React.ComponentProps<'div'> {
  icon?: React.ReactNode;
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action, className, ...props }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-2 p-8 text-center', className)} {...props}>
      {icon ? <div className="mb-1 text-fg-subtle [&_svg]:size-8 [&_svg]:stroke-[1.5]">{icon}</div> : null}
      <div className="text-sm font-medium text-fg">{title}</div>
      {description ? <div className="max-w-xs text-xs text-fg-muted">{description}</div> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
