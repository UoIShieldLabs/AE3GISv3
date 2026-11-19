import { formatDate } from '@/lib/time';
import type { LibraryLayout } from './model';
import { ItemMenu, OwnerLabel, StatusBadge, TopologyCard, type TopologyItem } from './TopologyCard';

export function CardGrid({ children }: { children: React.ReactNode }) {
  return <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">{children}</ul>;
}

/** The dense layout: one row per topology, the card's actions on the right. */
export function TopologyTable({ items, showOwner }: { items: TopologyItem[]; showOwner?: boolean }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border text-left text-2xs uppercase tracking-wide text-fg-subtle">
            <th className="px-3 py-2 font-medium">Name</th>
            <th className="px-3 py-2 font-medium">Status</th>
            {showOwner ? <th className="px-3 py-2 font-medium">Owner</th> : null}
            <th className="px-3 py-2 font-medium">Updated</th>
            <th className="px-3 py-2"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map(({ t, status = t.status, onOpen, marker, flags, primary, trailing, menu, owner }) => (
            <tr key={t.id} className="group hover:bg-hover/40">
              <td className="w-full max-w-0 px-3 py-1.5">
                <div className="flex min-w-0 items-center gap-2">
                  <button type="button" onClick={onOpen} className="min-w-0 truncate text-left text-[13px] font-medium hover:text-accent" title={t.name}>{t.name}</button>
                  {marker}
                  {flags ? <span className="flex min-w-0 items-center gap-2 text-2xs">{flags}</span> : null}
                </div>
              </td>
              <td className="px-3 py-1.5"><StatusBadge status={status} /></td>
              {showOwner ? <td className="max-w-32 px-3 py-1.5 text-fg-muted">{owner ? <OwnerLabel name={owner} /> : <span className="text-fg-subtle">you</span>}</td> : null}
              <td className="whitespace-nowrap px-3 py-1.5 text-fg-muted">{formatDate(t.updated_at)}</td>
              <td className="px-3 py-1.5">
                {/* Trailing first: Open and ⋯ line up down the column. */}
                <div className="flex items-center justify-end gap-1 whitespace-nowrap">
                  {trailing}
                  {primary}
                  {menu ? <ItemMenu>{menu}</ItemMenu> : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A section's topologies, as cards or rows (the viewer's choice). */
export function TopologyCollection({ items, layout, showOwner, empty }: {
  items: TopologyItem[];
  layout: LibraryLayout;
  showOwner?: boolean;
  /** Shown when there is nothing. */
  empty: React.ReactNode;
}) {
  if (items.length === 0) return <>{empty}</>;
  if (layout === 'list') return <TopologyTable items={items} showOwner={showOwner} />;
  return <CardGrid>{items.map((item) => <TopologyCard key={item.t.id} {...item} />)}</CardGrid>;
}
