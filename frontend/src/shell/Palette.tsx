import { useMemo, useState } from 'react';
import { Building2, GripVertical, Network, Search } from 'lucide-react';
import { useAppStore } from '@/store';
import { categoryLabel, colorFor, displayNameFor } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import { cn } from '@/lib/cn';
import type { Scope } from '@/lib/topology';
import { Input, Tooltip } from '@/ui';
import { setDragPayload, type PaletteItem } from '@/canvas/interactions/dnd';
import { useAddEntity } from '@/features/topology/AddEntityContext';
import { targetSiteFor, targetSubnetFor } from '@/features/topology/addTargets';

export function Palette({ scope }: { scope: Scope }) {
  const catalog = useAppStore((s) => s.catalog);
  const selection = useAppStore((s) => s.selection);
  const { requestAdd } = useAddEntity();
  const [query, setQuery] = useState('');

  const groups = useMemo(() => {
    const out = new Map<string, { type: string; name: string }[]>();
    if (!catalog) return out;
    const q = query.trim().toLowerCase();
    for (const [type, spec] of Object.entries(catalog.types)) {
      const name = spec.displayName || displayNameFor(type);
      if (q && !`${name} ${type} ${spec.category} ${spec.label}`.toLowerCase().includes(q)) continue;
      const cat = categoryLabel(spec.category ?? '');
      (out.get(cat) ?? out.set(cat, []).get(cat)!).push({ type, name });
    }
    return out;
  }, [catalog, query]);

  const subnetTarget = targetSubnetFor(scope, selection.nodeIds);
  const siteTarget = targetSiteFor(scope, selection.nodeIds);

  const add = (item: PaletteItem) => {
    if (item.kind === 'site') requestAdd(item, {});
    else if (item.kind === 'subnet') requestAdd(item, { siteId: siteTarget });
    else requestAdd(item, { subnetId: subnetTarget });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="p-2">
        <Input leading={<Search />} placeholder="Search devices…" value={query} onChange={(e) => setQuery(e.target.value)} className="h-7 text-xs" />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {!query ? (
          <Section title="Structure">
            <PaletteRow
              icon={<Building2 className="size-4 text-accent" />}
              label="Site"
              hint={scope.level === 'root' ? 'Add at the network level' : 'Sites are added at the Network level'}
              disabled={scope.level !== 'root'}
              item={{ kind: 'site' }}
              onAdd={add}
            />
            <PaletteRow
              icon={<Network className="size-4 text-info" />}
              label="Subnet"
              hint={siteTarget ? 'Adds a router and switch automatically' : 'Select a site first, or drag onto one'}
              disabled={!siteTarget}
              item={{ kind: 'subnet' }}
              onAdd={add}
            />
          </Section>
        ) : null}
        {[...groups.entries()].map(([cat, items]) => (
          <Section key={cat} title={cat}>
            {items.map((it) => (
              <PaletteRow
                key={it.type}
                icon={<NodeGlyph type={it.type} size={18} color={colorFor(it.type)} />}
                label={it.name}
                hint={subnetTarget ? undefined : 'Select a subnet first, or drag onto one'}
                disabled={!subnetTarget}
                item={{ kind: 'device', type: it.type }}
                onAdd={add}
              />
            ))}
          </Section>
        ))}
        {groups.size === 0 && query ? <p className="px-2 py-6 text-center text-xs text-fg-muted">No matching device types.</p> : null}
      </div>
      <div className="border-t border-border px-3 py-1.5 text-2xs text-fg-subtle">Click to add, or drag onto the canvas.</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-2">
      <div className="px-1 pb-1 pt-2 text-2xs font-semibold uppercase tracking-wide text-fg-subtle">{title}</div>
      <div className="flex flex-col gap-0.5">{children}</div>
    </div>
  );
}

function PaletteRow({ icon, label, hint, disabled, item, onAdd }: { icon: React.ReactNode; label: string; hint?: string; disabled?: boolean; item: PaletteItem; onAdd: (item: PaletteItem) => void }) {
  const row = (
    <div
      role="button"
      tabIndex={0}
      draggable
      onDragStart={(e) => setDragPayload(e, item)}
      onClick={() => !disabled && onAdd(item)}
      onKeyDown={(e) => { if (e.key === 'Enter' && !disabled) onAdd(item); }}
      className={cn(
        'group flex cursor-grab select-none items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors active:cursor-grabbing',
        'hover:bg-hover focus-visible:outline-2 focus-visible:outline-ring',
        disabled && 'opacity-60',
      )}
    >
      <span className="flex size-6 shrink-0 items-center justify-center rounded bg-surface-2">{icon}</span>
      <span className="flex-1 truncate font-medium">{label}</span>
      <GripVertical className="size-3.5 text-fg-subtle opacity-0 group-hover:opacity-100" />
    </div>
  );
  return hint ? <Tooltip content={hint} side="right">{row}</Tooltip> : row;
}
