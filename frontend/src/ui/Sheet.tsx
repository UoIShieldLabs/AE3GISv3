import { Dialog as RDialog } from 'radix-ui';
import { X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { IconButton } from './IconButton';
import { LAYER } from './layers';

export interface SheetProps extends Omit<React.ComponentProps<typeof RDialog.Content>, 'title'> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: React.ReactNode;
  description?: React.ReactNode;
  side?: 'right' | 'left' | 'bottom' | 'full';
  /** Width (right/left) or height (bottom). */
  size?: string;
  headerAction?: React.ReactNode;
  flush?: boolean;
}

const sideClass: Record<NonNullable<SheetProps['side']>, string> = {
  right: 'inset-y-0 right-0 h-full border-l animate-slide-in-right',
  left: 'inset-y-0 left-0 h-full border-r animate-slide-in-left',
  bottom: 'inset-x-0 bottom-0 w-full border-t animate-slide-in-bottom',
  full: 'inset-4 rounded-xl border animate-pop',
};

/** Edge-anchored dialog for large content (Purdue view, logs, previews). */
export function Sheet({ open, onOpenChange, title, description, side = 'right', size, headerAction, flush, className, children, ...props }: SheetProps) {
  const style =
    side === 'right' || side === 'left' ? { width: size ?? '480px' } : side === 'bottom' ? { height: size ?? '60vh' } : undefined;
  return (
    <RDialog.Root open={open} onOpenChange={onOpenChange}>
      <RDialog.Portal>
        <RDialog.Overlay className={cn("fixed inset-0 bg-black/50 animate-fade", LAYER.overlay)} />
        <RDialog.Content
          className={cn(
            'fixed flex max-w-full flex-col border-border bg-surface text-fg shadow-lg outline-none',
            LAYER.modal,
            sideClass[side],
            className,
          )}
          style={style}
          {...props}
        >
          <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
            <div className="min-w-0">
              <RDialog.Title className="text-sm font-semibold">{title}</RDialog.Title>
              <RDialog.Description className={description ? 'text-xs text-fg-muted' : 'sr-only'}>
                {description ?? (typeof title === 'string' ? title : 'Panel')}
              </RDialog.Description>
            </div>
            <div className="flex items-center gap-1">
              {headerAction}
              <RDialog.Close asChild>
                <IconButton label="Close" size="icon-sm" tooltip={false}><X /></IconButton>
              </RDialog.Close>
            </div>
          </div>
          <div className={cn('min-h-0 flex-1 overflow-auto', !flush && 'p-4')}>{children}</div>
        </RDialog.Content>
      </RDialog.Portal>
    </RDialog.Root>
  );
}
