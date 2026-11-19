import { useEffect, useRef } from 'react';
import { Activity, LayoutGrid, List, Search, X } from 'lucide-react';
import { Button, IconButton, Input, Select } from '@/ui';
import { cn } from '@/lib/cn';
import type { LibraryLayout, LibrarySort } from './model';

const SORTS: { value: LibrarySort; label: string }[] = [
  { value: 'recent', label: 'Recent' },
  { value: 'name', label: 'Name' },
  { value: 'status', label: 'Status' },
];

/** Over a section: search (`/` focuses it), and, where the section has them,
 *  extra filters, running only, sort and grid / list. */
export function LibraryToolbar({ q, onQuery, placeholder = 'Search', runningOnly, onRunningOnly, sort, onSort, layout, onLayout, children }: {
  q: string;
  onQuery: (q: string) => void;
  placeholder?: string;
  runningOnly?: boolean;
  onRunningOnly?: (on: boolean) => void;
  sort?: LibrarySort;
  onSort?: (sort: LibrarySort) => void;
  layout?: LibraryLayout;
  onLayout?: (layout: LibraryLayout) => void;
  /** Section filters, after the search box. */
  children?: React.ReactNode;
}) {
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      if (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName))) return;
      e.preventDefault();
      searchRef.current?.focus();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="w-full sm:w-64">
        <Input
          ref={searchRef}
          value={q}
          onChange={(e) => onQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Escape' && q) { e.preventDefault(); onQuery(''); } }}
          placeholder={placeholder}
          aria-label="Search the library"
          leading={<Search />}
          trailing={q ? <IconButton label="Clear search" size="icon-xs" onClick={() => onQuery('')}><X /></IconButton> : null}
        />
      </div>
      {children}
      <div className="ml-auto flex items-center gap-1.5">
        {onRunningOnly ? (
          <Button size="sm" variant={runningOnly ? 'secondary' : 'ghost'} aria-pressed={!!runningOnly} onClick={() => onRunningOnly(!runningOnly)}>
            <Activity /> Running only
          </Button>
        ) : null}
        {onSort && sort ? <Select size="sm" value={sort} onValueChange={onSort} options={SORTS} aria-label="Sort" className="w-24" /> : null}
        {onLayout && layout ? (
          <div role="group" aria-label="Layout" className="flex items-center gap-0.5 rounded-md bg-surface-2 p-0.5">
            {([['grid', 'Grid', LayoutGrid], ['list', 'List', List]] as const).map(([id, label, Icon]) => (
              <IconButton
                key={id}
                label={label}
                size="icon-xs"
                aria-pressed={layout === id}
                onClick={() => onLayout(id)}
                className={cn(layout === id && 'bg-surface text-fg shadow-sm')}
              >
                <Icon />
              </IconButton>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
