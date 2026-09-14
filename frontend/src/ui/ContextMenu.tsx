import { ContextMenu as R } from 'radix-ui';
import { Check, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/cn';
import { menuContentClass, menuIndentClass, menuItemClass, menuLabelClass, menuSeparatorClass, menuShortcutClass } from './menu-styles';

export const ContextMenu = R.Root;
export const ContextMenuTrigger = R.Trigger;
export const ContextMenuGroup = R.Group;
export const ContextMenuSub = R.Sub;

export function ContextMenuContent({ className, ...props }: React.ComponentProps<typeof R.Content>) {
  return (
    <R.Portal>
      <R.Content collisionPadding={8} className={cn(menuContentClass, className)} {...props} />
    </R.Portal>
  );
}

export function ContextMenuSubContent({ className, ...props }: React.ComponentProps<typeof R.SubContent>) {
  return (
    <R.Portal>
      <R.SubContent sideOffset={2} alignOffset={-4} className={cn(menuContentClass, className)} {...props} />
    </R.Portal>
  );
}

export interface ContextMenuItemProps extends React.ComponentProps<typeof R.Item> {
  variant?: 'default' | 'danger';
  shortcut?: string;
  inset?: boolean;
}

export function ContextMenuItem({ className, variant = 'default', shortcut, inset, children, ...props }: ContextMenuItemProps) {
  return (
    <R.Item data-variant={variant} className={cn(menuItemClass, inset && menuIndentClass, className)} {...props}>
      {children}
      {shortcut ? <span className={menuShortcutClass}>{shortcut}</span> : null}
    </R.Item>
  );
}

export function ContextMenuCheckboxItem({ className, children, ...props }: React.ComponentProps<typeof R.CheckboxItem>) {
  return (
    <R.CheckboxItem className={cn(menuItemClass, menuIndentClass, className)} {...props}>
      <span className="absolute left-2 flex size-3.5 items-center justify-center">
        <R.ItemIndicator><Check className="size-3.5" /></R.ItemIndicator>
      </span>
      {children}
    </R.CheckboxItem>
  );
}

export function ContextMenuSubTrigger({ className, inset, children, ...props }: React.ComponentProps<typeof R.SubTrigger> & { inset?: boolean }) {
  return (
    <R.SubTrigger className={cn(menuItemClass, 'data-[state=open]:bg-hover', inset && menuIndentClass, className)} {...props}>
      {children}
      <ChevronRight className="ml-auto" />
    </R.SubTrigger>
  );
}

export function ContextMenuLabel({ className, ...props }: React.ComponentProps<typeof R.Label>) {
  return <R.Label className={cn(menuLabelClass, className)} {...props} />;
}

export function ContextMenuSeparator({ className, ...props }: React.ComponentProps<typeof R.Separator>) {
  return <R.Separator className={cn(menuSeparatorClass, className)} {...props} />;
}
