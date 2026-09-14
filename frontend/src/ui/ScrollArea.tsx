import { ScrollArea as R } from 'radix-ui';
import { cn } from '@/lib/cn';

export interface ScrollAreaProps extends React.ComponentProps<typeof R.Root> {
  orientation?: 'vertical' | 'horizontal' | 'both';
  viewportClassName?: string;
}

export function ScrollArea({ className, viewportClassName, orientation = 'vertical', children, ...props }: ScrollAreaProps) {
  return (
    <R.Root className={cn('relative overflow-hidden', className)} {...props}>
      <R.Viewport className={cn('size-full rounded-[inherit] [&>div]:!block', viewportClassName)}>{children}</R.Viewport>
      {orientation !== 'horizontal' ? (
        <R.Scrollbar orientation="vertical" className="flex w-2 touch-none select-none p-px transition-colors">
          <R.Thumb className="relative flex-1 rounded-full bg-border-strong" />
        </R.Scrollbar>
      ) : null}
      {orientation !== 'vertical' ? (
        <R.Scrollbar orientation="horizontal" className="flex h-2 touch-none select-none flex-col p-px">
          <R.Thumb className="relative flex-1 rounded-full bg-border-strong" />
        </R.Scrollbar>
      ) : null}
      <R.Corner />
    </R.Root>
  );
}
