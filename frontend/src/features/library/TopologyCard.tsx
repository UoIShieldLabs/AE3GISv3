import { Clock, Ellipsis, UserRound } from 'lucide-react';
import type { TopologySummary } from '@/api/client';
import { Badge, DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, IconButton } from '@/ui';
import { cn } from '@/lib/cn';
import { formatDate } from '@/lib/time';

const STATUS_TONE: Record<string, 'success' | 'neutral' | 'warning' | 'danger'> = {
  deployed: 'success', idle: 'neutral', deploying: 'warning', destroying: 'warning', error: 'danger',
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? 'neutral'} dot={status === 'deployed' ? 'pulse' : true}>{status}</Badge>;
}

/** A quiet state on a card's date line: a dot and a word (Published, Updated). */
export function Flag({ tone, title, children }: { tone: 'accent' | 'warning'; title?: string; children: React.ReactNode }) {
  return (
    <span title={title} className={cn('flex min-w-0 items-center gap-1', tone === 'accent' ? 'text-accent' : 'text-warning')}>
      <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-current" />
      <span className="truncate">{children}</span>
    </span>
  );
}

/** One topology as a section shows it, in a card or a list row: the same
 *  actions either way. */
export interface TopologyItem {
  t: TopologySummary;
  /** Shown instead of the topology's own (a lesson shows its copy's). */
  status?: string;
  onOpen: () => void;
  /** A small icon after the name. */
  marker?: React.ReactNode;
  /** `Flag`s after the date. */
  flags?: React.ReactNode;
  primary: React.ReactNode;
  /** Right of the primary action, before the menu (e.g. the publish switch). */
  trailing?: React.ReactNode;
  /** Items of the "⋯" menu. */
  menu?: React.ReactNode;
  /** Whose it is, in a section that mixes owners (Running). */
  owner?: string;
}

export function ItemMenu({ children }: { children: React.ReactNode }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <IconButton label="More" size="icon-sm" className="opacity-60 group-hover:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100"><Ellipsis /></IconButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">{children}</DropdownMenuContent>
    </DropdownMenu>
  );
}

export function OwnerLabel({ name }: { name: string }) {
  return (
    <span className="flex min-w-0 items-center gap-1" title={`${name}'s`}>
      <UserRound className="size-3 shrink-0" /> <span className="truncate">{name}</span>
    </span>
  );
}

/** One topology: name, when, status, one primary action and a "⋯" menu.
 *  Everything on one line truncates, so long names never push the card wider. */
export function TopologyCard({ t, status = t.status, onOpen, marker, flags, primary, trailing, menu, owner }: TopologyItem) {
  return (
    <li className="group flex min-w-0 flex-col gap-2 rounded-xl border border-border bg-surface p-4 shadow-sm transition-colors hover:border-border-strong">
      <div className="flex items-start justify-between gap-2">
        <button type="button" onClick={onOpen} className="min-w-0 flex-1 text-left">
          <div className="flex min-w-0 items-center gap-1.5">
            <span className="truncate text-sm font-medium hover:text-accent" title={t.name}>{t.name}</span>
            {marker}
          </div>
          <div className="mt-0.5 flex min-w-0 items-center gap-2 text-2xs text-fg-muted">
            {owner ? <OwnerLabel name={owner} /> : null}
            <span className="flex shrink-0 items-center gap-1"><Clock className="size-3" /> {formatDate(t.updated_at)}</span>
            {flags}
          </div>
        </button>
        <StatusBadge status={status} />
      </div>
      <div className="mt-auto flex items-center gap-1 pt-1">
        {primary}
        <div className="ml-auto flex items-center gap-1">
          {trailing}
          {menu ? <ItemMenu>{menu}</ItemMenu> : null}
        </div>
      </div>
    </li>
  );
}
