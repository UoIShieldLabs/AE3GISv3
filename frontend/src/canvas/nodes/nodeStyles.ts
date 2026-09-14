import { cn } from '@/lib/cn';

/** Card chrome shared by every collapsed node kind. */
export function nodeCardClass(selected: boolean | undefined, extra?: string): string {
  return cn(
    'group/node relative flex select-none rounded-lg border bg-surface text-fg shadow-sm',
    'transition-[box-shadow,border-color,background-color] duration-100',
    selected ? 'border-accent ring-2 ring-accent/30' : 'border-border hover:border-border-strong hover:shadow-md',
    extra,
  );
}

/** Four handles, all `source` type; connectionMode="loose" lets any pair connect. */
export const HANDLE_IDS = ['top', 'right', 'bottom', 'left'] as const;
