import { useState } from 'react';
import { Check, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/cn';
import { inputClassName } from './Input';
import { Popover, PopoverContent, PopoverTrigger } from './Popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from './Command';

export interface ComboboxOption<T extends string = string> {
  value: T;
  label: string;
  /** Extra searchable text (e.g. category, aliases). */
  keywords?: string[];
  description?: string;
  icon?: React.ReactNode;
  group?: string;
  disabled?: boolean;
}

export interface ComboboxProps<T extends string = string> {
  value: T | undefined;
  onValueChange: (value: T) => void;
  options: ComboboxOption<T>[];
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
  id?: string;
  className?: string;
  mono?: boolean;
  /** Custom trigger content when a value is selected. */
  renderValue?: (option: ComboboxOption<T>) => React.ReactNode;
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
}

/** Searchable select built from Popover + cmdk. */
export function Combobox<T extends string = string>({
  value, onValueChange, options, placeholder = 'Select…', searchPlaceholder = 'Search…', emptyText = 'No results.',
  disabled, id, className, mono, renderValue, ...aria
}: ComboboxProps<T>) {
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.value === value);
  const groups = new Map<string | undefined, ComboboxOption<T>[]>();
  for (const o of options) {
    const list = groups.get(o.group) ?? [];
    list.push(o);
    groups.set(o.group, list);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          id={id}
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn(inputClassName, 'items-center justify-between gap-2 text-left', mono && 'font-mono text-xs', !selected && 'text-fg-subtle', className)}
          {...aria}
        >
          <span className="flex min-w-0 items-center gap-2 truncate">
            {selected ? (renderValue ? renderValue(selected) : <>{selected.icon}<span className="truncate">{selected.label}</span></>) : placeholder}
          </span>
          <ChevronsUpDown className="size-3.5 shrink-0 text-fg-subtle" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] min-w-56 p-0">
        <Command>
          <CommandInput placeholder={searchPlaceholder} autoFocus />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            {[...groups.entries()].map(([group, items]) => (
              <CommandGroup key={group ?? '__none'} heading={group}>
                {items.map((o) => (
                  <CommandItem
                    key={o.value}
                    value={o.value}
                    keywords={[o.label, ...(o.keywords ?? [])]}
                    disabled={o.disabled}
                    onSelect={() => { onValueChange(o.value); setOpen(false); }}
                    className={cn(mono && 'font-mono text-xs')}
                  >
                    {o.icon}
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate">{o.label}</span>
                      {o.description ? <span className="truncate text-2xs text-fg-subtle">{o.description}</span> : null}
                    </span>
                    <Check className={cn('ml-auto size-3.5', o.value === value ? 'opacity-100' : 'opacity-0')} />
                  </CommandItem>
                ))}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
