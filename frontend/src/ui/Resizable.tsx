import { Group, Panel, Separator, type GroupProps, type PanelProps, type SeparatorProps } from 'react-resizable-panels';
import { cn } from '@/lib/cn';

export type { GroupProps as ResizableGroupProps, PanelProps as ResizablePanelProps };

export function ResizableGroup({ className, ...props }: GroupProps) {
  return <Group className={cn('flex size-full', props.orientation === 'vertical' ? 'flex-col' : 'flex-row', className)} {...props} />;
}

export function ResizablePanel({ className, ...props }: PanelProps) {
  return <Panel className={cn('min-h-0 min-w-0', className)} {...props} />;
}

/** Thin, hit-area-padded resize handle with a hover/active highlight. */
export function ResizableHandle({ className, ...props }: SeparatorProps) {
  return (
    <Separator
      className={cn(
        'group/handle relative z-10 shrink-0 bg-border transition-colors',
        'data-[orientation=vertical]:h-px data-[orientation=vertical]:w-full data-[orientation=vertical]:cursor-row-resize',
        'data-[orientation=horizontal]:w-px data-[orientation=horizontal]:h-full data-[orientation=horizontal]:cursor-col-resize',
        'hover:bg-accent data-[resize-handle-active]:bg-accent data-[resizing]:bg-accent',
        // enlarge hit area
        'after:absolute after:content-[""] data-[orientation=horizontal]:after:-inset-x-1 data-[orientation=horizontal]:after:inset-y-0',
        'data-[orientation=vertical]:after:-inset-y-1 data-[orientation=vertical]:after:inset-x-0',
        className,
      )}
      {...props}
    />
  );
}
