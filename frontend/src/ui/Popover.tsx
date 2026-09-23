import { Popover as R } from 'radix-ui';
import { cn } from '@/lib/cn';
import { LAYER } from './layers';

export const Popover = R.Root;
export const PopoverTrigger = R.Trigger;
export const PopoverAnchor = R.Anchor;
export const PopoverClose = R.Close;

export function PopoverContent({ className, align = 'start', sideOffset = 6, ...props }: React.ComponentProps<typeof R.Content>) {
  return (
    <R.Portal>
      <R.Content
        align={align}
        sideOffset={sideOffset}
        collisionPadding={8}
        className={cn(
          'w-72 rounded-lg border border-border bg-elevated p-3 text-fg shadow-lg outline-none animate-pop',
          LAYER.floating,
          className,
        )}
        {...props}
      />
    </R.Portal>
  );
}
