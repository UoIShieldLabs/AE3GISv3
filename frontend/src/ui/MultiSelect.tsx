import { useState } from 'react';
import { Check, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/cn';
import { inputClassName } from './Input';
import { Popover, PopoverContent, PopoverTrigger } from './Popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from './Command';
import type { ComboboxOption } from './Combobox';

export interface MultiSelectProps<T extends string = string> {
  value: readonly T[];
  onValueChange: (value: T[]) => void;
  options: ComboboxOption<T>[];
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
  id?: string;
  className?: string;
  size?: 'sm' | 'md';
  'aria-label'?: string;
}

/** Searchable multi-value select (Popover + cmdk); the list stays open while
 *  picking. The trigger names up to two picks, then counts. */
export function MultiSelect<T extends string = string>({
  value, onValueChange, options, placeholder = 'Select…', searchPlaceholder = 'Search…', emptyText = 'No results.',
  disabled, id, className, size = 'md', ...aria
}: MultiSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const chosen = new Set(value);
  const picked = options.filter((o) => chosen.has(o.value));
  const groups = new Map<string | undefined, ComboboxOption<T>[]>();
  for (const o of options) {
    const list = groups.get(o.group) ?? [];
    list.push(o);
    groups.set(o.group, list);
  }
  const toggle = (v: T) => onValueChange(chosen.has(v) ? value.filter((x) => x !== v) : [...value, v]);
  const summary = picked.length === 0 ? placeholder : picked.length <= 2 ? picked.map((o) => o.label).join(', ') : `${picked.length} selected`;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          id={id}
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn(inputClassName, 'items-center justify-between gap-2 text-left', size === 'sm' && 'h-7 text-xs', !picked.length && 'text-fg-subtle', className)}
          {...aria}
        >
          <span className="truncate">{summary}</span>
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
                    onSelect={() => toggle(o.value)}
                  >
                    {o.icon}
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate">{o.label}</span>
                      {o.description ? <span className="truncate text-2xs text-fg-subtle">{o.description}</span> : null}
                    </span>
                    <Check className={cn('ml-auto size-3.5', chosen.has(o.value) ? 'opacity-100' : 'opacity-0')} />
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
