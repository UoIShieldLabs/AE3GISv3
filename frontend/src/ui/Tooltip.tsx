import { Tooltip as RTooltip } from 'radix-ui';
import { cn } from '@/lib/cn';
import { LAYER } from './layers';

export const TooltipProvider = RTooltip.Provider;

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  side?: 'top' | 'right' | 'bottom' | 'left';
  align?: 'start' | 'center' | 'end';
  shortcut?: string;
  delayDuration?: number;
  className?: string;
}

/** Wraps a single trigger element with a themed tooltip. */
export function Tooltip({ content, children, side = 'bottom', align = 'center', shortcut, delayDuration = 400, className }: TooltipProps) {
  if (content === null || content === undefined || content === '') return children;
  return (
    <RTooltip.Root delayDuration={delayDuration}>
      <RTooltip.Trigger asChild>{children}</RTooltip.Trigger>
      <RTooltip.Portal>
        <RTooltip.Content
          side={side}
          align={align}
          sideOffset={6}
          collisionPadding={8}
          className={cn(
            'flex items-center gap-2 rounded-md border border-border bg-elevated px-2 py-1 text-xs text-fg shadow-md',
            LAYER.tooltip,
            'animate-pop',
            className,
          )}
        >
          {content}
          {shortcut ? <span className="font-mono text-2xs text-fg-subtle">{shortcut}</span> : null}
        </RTooltip.Content>
      </RTooltip.Portal>
    </RTooltip.Root>
  );
}
