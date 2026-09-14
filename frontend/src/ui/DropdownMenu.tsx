import { DropdownMenu as R } from 'radix-ui';
import { Check, ChevronRight, Circle } from 'lucide-react';
import { cn } from '@/lib/cn';
import { menuContentClass, menuIndentClass, menuItemClass, menuLabelClass, menuSeparatorClass, menuShortcutClass } from './menu-styles';

export const DropdownMenu = R.Root;
export const DropdownMenuTrigger = R.Trigger;
export const DropdownMenuGroup = R.Group;
export const DropdownMenuSub = R.Sub;
export const DropdownMenuRadioGroup = R.RadioGroup;

export function DropdownMenuContent({ className, sideOffset = 4, ...props }: React.ComponentProps<typeof R.Content>) {
  return (
    <R.Portal>
      <R.Content sideOffset={sideOffset} collisionPadding={8} className={cn(menuContentClass, className)} {...props} />
    </R.Portal>
  );
}

export function DropdownMenuSubContent({ className, ...props }: React.ComponentProps<typeof R.SubContent>) {
  return (
    <R.Portal>
      <R.SubContent sideOffset={2} alignOffset={-4} className={cn(menuContentClass, className)} {...props} />
    </R.Portal>
  );
}

export interface DropdownMenuItemProps extends React.ComponentProps<typeof R.Item> {
  variant?: 'default' | 'danger';
  shortcut?: string;
  inset?: boolean;
}

export function DropdownMenuItem({ className, variant = 'default', shortcut, inset, children, ...props }: DropdownMenuItemProps) {
  return (
    <R.Item data-variant={variant} className={cn(menuItemClass, inset && menuIndentClass, className)} {...props}>
      {children}
      {shortcut ? <span className={menuShortcutClass}>{shortcut}</span> : null}
    </R.Item>
  );
}

export function DropdownMenuCheckboxItem({ className, children, ...props }: React.ComponentProps<typeof R.CheckboxItem>) {
  return (
    <R.CheckboxItem className={cn(menuItemClass, menuIndentClass, className)} {...props}>
      <span className="absolute left-2 flex size-3.5 items-center justify-center">
        <R.ItemIndicator><Check className="size-3.5" /></R.ItemIndicator>
      </span>
      {children}
    </R.CheckboxItem>
  );
}

export function DropdownMenuRadioItem({ className, children, ...props }: React.ComponentProps<typeof R.RadioItem>) {
  return (
    <R.RadioItem className={cn(menuItemClass, menuIndentClass, className)} {...props}>
      <span className="absolute left-2 flex size-3.5 items-center justify-center">
        <R.ItemIndicator><Circle className="size-2 fill-current" /></R.ItemIndicator>
      </span>
      {children}
    </R.RadioItem>
  );
}

export function DropdownMenuSubTrigger({ className, inset, children, ...props }: React.ComponentProps<typeof R.SubTrigger> & { inset?: boolean }) {
  return (
    <R.SubTrigger className={cn(menuItemClass, 'data-[state=open]:bg-hover', inset && menuIndentClass, className)} {...props}>
      {children}
      <ChevronRight className="ml-auto" />
    </R.SubTrigger>
  );
}

export function DropdownMenuLabel({ className, ...props }: React.ComponentProps<typeof R.Label>) {
  return <R.Label className={cn(menuLabelClass, className)} {...props} />;
}

export function DropdownMenuSeparator({ className, ...props }: React.ComponentProps<typeof R.Separator>) {
  return <R.Separator className={cn(menuSeparatorClass, className)} {...props} />;
}
