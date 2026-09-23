import { Select as R } from 'radix-ui';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/cn';
import { inputClassName } from './Input';
import { menuItemClass, menuLabelClass, menuSeparatorClass } from './menu-styles';
import { LAYER } from './layers';

export interface SelectOption<T extends string = string> {
  value: T;
  label: React.ReactNode;
  disabled?: boolean;
  group?: string;
}

export interface SelectProps<T extends string = string> {
  value: T | undefined;
  onValueChange: (value: T) => void;
  options: SelectOption<T>[];
  placeholder?: string;
  disabled?: boolean;
  id?: string;
  className?: string;
  size?: 'sm' | 'md';
  mono?: boolean;
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
}

/** Simple single-value select over a flat (optionally grouped) option list. */
export function Select<T extends string = string>({ value, onValueChange, options, placeholder = 'Select…', disabled, id, className, size = 'md', mono, ...aria }: SelectProps<T>) {
  const groups = new Map<string | undefined, SelectOption<T>[]>();
  for (const o of options) {
    const list = groups.get(o.group) ?? [];
    list.push(o);
    groups.set(o.group, list);
  }
  return (
    <R.Root value={value} onValueChange={onValueChange as (v: string) => void} disabled={disabled}>
      <R.Trigger
        id={id}
        className={cn(
          inputClassName,
          'items-center justify-between gap-2 text-left data-[placeholder]:text-fg-subtle',
          size === 'sm' && 'h-7 text-xs',
          mono && 'font-mono text-xs',
          className,
        )}
        {...aria}
      >
        <span className="truncate"><R.Value placeholder={placeholder} /></span>
        <R.Icon asChild><ChevronDown className="size-3.5 shrink-0 text-fg-subtle" /></R.Icon>
      </R.Trigger>
      <R.Portal>
        <R.Content
          position="popper"
          sideOffset={4}
          className={cn(
            "max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-lg border border-border bg-elevated p-1 text-fg shadow-lg animate-pop",
            LAYER.floating,
          )}
        >
          <R.ScrollUpButton className="flex justify-center py-1 text-fg-subtle"><ChevronUp className="size-3.5" /></R.ScrollUpButton>
          <R.Viewport>
            {[...groups.entries()].map(([group, items], gi) => (
              <R.Group key={group ?? '__none'}>
                {group ? <R.Label className={menuLabelClass}>{group}</R.Label> : null}
                {gi > 0 && !group ? <R.Separator className={menuSeparatorClass} /> : null}
                {items.map((o) => (
                  <R.Item key={o.value} value={o.value} disabled={o.disabled} className={cn(menuItemClass, 'pl-7', mono && 'font-mono text-xs')}>
                    <span className="absolute left-2 flex size-3.5 items-center justify-center">
                      <R.ItemIndicator><Check className="size-3.5" /></R.ItemIndicator>
                    </span>
                    <R.ItemText>{o.label}</R.ItemText>
                  </R.Item>
                ))}
              </R.Group>
            ))}
          </R.Viewport>
          <R.ScrollDownButton className="flex justify-center py-1 text-fg-subtle"><ChevronDown className="size-3.5" /></R.ScrollDownButton>
        </R.Content>
      </R.Portal>
    </R.Root>
  );
}
