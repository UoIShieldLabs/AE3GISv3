import { Dialog as RDialog } from 'radix-ui';
import { X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { IconButton } from './IconButton';

export const DialogRoot = RDialog.Root;
export const DialogTrigger = RDialog.Trigger;
export const DialogClose = RDialog.Close;

export interface DialogContentProps extends Omit<React.ComponentProps<typeof RDialog.Content>, 'title'> {
  title: React.ReactNode;
  description?: React.ReactNode;
  /** Width preset or explicit CSS width. */
  size?: 'sm' | 'md' | 'lg' | 'xl' | (string & {});
  hideClose?: boolean;
  footer?: React.ReactNode;
  /** Remove body padding (for tables / lists). */
  flush?: boolean;
}

const sizes: Record<string, string> = { sm: '360px', md: '460px', lg: '620px', xl: '820px' };

export function DialogContent({ title, description, size = 'md', hideClose, footer, flush, className, children, ...props }: DialogContentProps) {
  const width = sizes[size] ?? size;
  return (
    <RDialog.Portal>
      <RDialog.Overlay className="fixed inset-0 z-[80] bg-black/50 backdrop-blur-[1px] animate-fade" />
      <RDialog.Content
        className={cn(
          'fixed left-1/2 top-1/2 z-[81] flex max-h-[85vh] w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 flex-col',
          'rounded-xl border border-border bg-surface text-fg shadow-lg outline-none animate-pop',
          className,
        )}
        style={{ maxWidth: width }}
        {...props}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-3.5">
          <div className="min-w-0">
            <RDialog.Title className="text-sm font-semibold leading-5">{title}</RDialog.Title>
            {description ? (
              <RDialog.Description className="mt-0.5 text-xs text-fg-muted">{description}</RDialog.Description>
            ) : (
              <RDialog.Description className="sr-only">{typeof title === 'string' ? title : 'Dialog'}</RDialog.Description>
            )}
          </div>
          {!hideClose ? (
            <RDialog.Close asChild>
              <IconButton label="Close" size="icon-sm" tooltip={false} className="-mr-1.5 -mt-1">
                <X />
              </IconButton>
            </RDialog.Close>
          ) : null}
        </div>
        <div className={cn('min-h-0 flex-1 overflow-y-auto', !flush && 'px-5 py-4')}>{children}</div>
        {footer ? <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">{footer}</div> : null}
      </RDialog.Content>
    </RDialog.Portal>
  );
}

/** Convenience: controlled dialog in one component. */
export interface DialogProps extends Omit<DialogContentProps, 'title'> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: React.ReactNode;
}

export function Dialog({ open, onOpenChange, ...content }: DialogProps) {
  return (
    <RDialog.Root open={open} onOpenChange={onOpenChange}>
      <DialogContent {...content} />
    </RDialog.Root>
  );
}
