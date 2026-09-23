import { useState } from 'react';
import { Building2, ChevronDown, ChevronRight, GripVertical, Network, Search } from 'lucide-react';
import { useAppStore } from '@/store';
import { colorFor } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import type { CatalogTypeNode, CatalogVariant } from '@/catalog/tree';
import { useCatalogTree } from '@/catalog/useCatalogTree';
import { cn } from '@/lib/cn';
import type { Scope } from '@/lib/topology';
import { Badge, Input, Tooltip } from '@/ui';
import { setDragPayload, type PaletteItem } from '@/canvas/interactions/dnd';
import { useAddEntity } from '@/features/topology/AddEntityContext';
import { targetSiteFor, targetSubnetFor } from '@/features/topology/addTargets';
import { ImageStatusDot } from '@/features/images/ImageStatusBadge';
import { useImageStatus } from '@/features/images/status';

export function Palette({ scope }: { scope: Scope }) {
  const selection = useAppStore((s) => s.selection);
  const collapsed = useAppStore((s) => s.collapsedCategories);
  const toggleCategory = useAppStore((s) => s.toggleCategory);
  const { requestAdd } = useAddEntity();
  const [query, setQuery] = useState('');
  const [openTypes, setOpenTypes] = useState<Record<string, boolean>>({});
  const tree = useCatalogTree(query);
  const searching = query.trim().length > 0;

  const subnetTarget = targetSubnetFor(scope, selection.nodeIds);
  const siteTarget = targetSiteFor(scope, selection.nodeIds);

  const add = (item: PaletteItem) => {
    if (item.kind === 'site') requestAdd(item, {});
    else if (item.kind === 'subnet') requestAdd(item, { siteId: siteTarget });
    else requestAdd(item, { subnetId: subnetTarget });
  };
  const deviceHint = subnetTarget ? undefined : 'Select a subnet first, or drag onto one';

  return (
    <div className="flex h-full flex-col">
      <div className="p-2">
        <Input leading={<Search />} placeholder="Search devices and images…" value={query} onChange={(e) => setQuery(e.target.value)} className="h-7 text-xs" />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {!searching ? (
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
        {tree.map((cat) => {
          const isCollapsed = !searching && collapsed.includes(cat.id);
          return (
            <Section key={cat.id} title={cat.label} count={cat.types.length} collapsed={isCollapsed} onToggle={searching ? undefined : () => toggleCategory(cat.id)}>
              {cat.types.map((node) => (
                <TypeRow
                  key={node.type}
                  node={node}
                  open={!!openTypes[node.type]}
                  onToggle={() => setOpenTypes((o) => ({ ...o, [node.type]: !o[node.type] }))}
                  hint={deviceHint}
                  disabled={!subnetTarget}
                  onAdd={add}
                />
              ))}
            </Section>
          );
        })}
        {tree.length === 0 && searching ? <p className="px-2 py-6 text-center text-xs text-fg-muted">No matching devices or images.</p> : null}
      </div>
      <div className="border-t border-border px-3 py-1.5 text-2xs text-fg-subtle">Click to add, or drag onto the canvas.</div>
    </div>
  );
}

function Section({ title, count, collapsed, onToggle, children }: { title: string; count?: number; collapsed?: boolean; onToggle?: () => void; children: React.ReactNode }) {
  const heading = (
    <>
      {onToggle ? (collapsed ? <ChevronRight className="size-3" /> : <ChevronDown className="size-3" />) : null}
      <span>{title}</span>
      {collapsed && count ? <span className="ml-auto font-normal normal-case tracking-normal">{count}</span> : null}
    </>
  );
  return (
    <div className="mb-2">
      {onToggle ? (
        <button type="button" onClick={onToggle} aria-expanded={!collapsed} className="flex w-full items-center gap-1 px-1 pb-1 pt-2 text-2xs font-semibold uppercase tracking-wide text-fg-subtle hover:text-fg">
          {heading}
        </button>
      ) : (
        <div className="flex items-center gap-1 px-1 pb-1 pt-2 text-2xs font-semibold uppercase tracking-wide text-fg-subtle">{heading}</div>
      )}
      {collapsed ? null : <div className="flex flex-col gap-0.5">{children}</div>}
    </div>
  );
}

function TypeRow({ node, open, onToggle, hint, disabled, onAdd }: { node: CatalogTypeNode; open: boolean; onToggle: () => void; hint?: string; disabled?: boolean; onAdd: (item: PaletteItem) => void }) {
  // A search that matched variants shows them directly; otherwise types with
  // several variants get an expander.
  const expandable = !node.matchedVariants && node.variants.length > 1;
  const showVariants = node.matchedVariants || (expandable && open);
  const def = node.variants.find((v) => v.isDefault) ?? node.variants[0];
  const defStatus = useImageStatus(def?.built ? def.ref : undefined);
  return (
    <>
      <PaletteRow
        icon={<NodeGlyph type={node.type} size={18} color={colorFor(node.type)} />}
        label={node.name}
        hint={hint}
        disabled={disabled}
        item={{ kind: 'device', type: node.type }}
        onAdd={onAdd}
        trailing={
          <>
            <ImageStatusDot image={defStatus} />
            {expandable ? (
              <button
                type="button"
                aria-label={open ? `Hide ${node.name} variants` : `Show ${node.name} variants`}
                aria-expanded={open}
                onClick={(e) => { e.stopPropagation(); onToggle(); }}
                onKeyDown={(e) => e.stopPropagation()}
                className="flex items-center gap-0.5 rounded px-1 text-2xs text-fg-subtle hover:bg-active hover:text-fg"
              >
                {node.variants.length}
                {open ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
              </button>
            ) : null}
          </>
        }
      />
      {showVariants ? (
        <div className="ml-4 flex flex-col gap-0.5 border-l border-border pl-1.5">
          {node.variants.map((v) => <VariantRow key={v.ref} type={node.type} variant={v} hint={hint} disabled={disabled} onAdd={onAdd} />)}
        </div>
      ) : null}
    </>
  );
}

function VariantRow({ type, variant, hint, disabled, onAdd }: { type: string; variant: CatalogVariant; hint?: string; disabled?: boolean; onAdd: (item: PaletteItem) => void }) {
  const status = useImageStatus(variant.built ? variant.ref : undefined);
  const item: PaletteItem = variant.isDefault ? { kind: 'device', type } : { kind: 'device', type, image: variant.ref };
  return (
    <PaletteRow
      label={variant.name}
      hint={hint ?? (variant.description || variant.ref)}
      disabled={disabled}
      item={item}
      onAdd={onAdd}
      compact
      trailing={
        <>
          {variant.stability === 'experimental' ? <Badge tone="outline" className="px-1">exp</Badge> : null}
          <ImageStatusDot image={status} />
        </>
      }
    />
  );
}

function PaletteRow({ icon, label, hint, disabled, item, onAdd, trailing, compact }: { icon?: React.ReactNode; label: string; hint?: string; disabled?: boolean; item: PaletteItem; onAdd: (item: PaletteItem) => void; trailing?: React.ReactNode; compact?: boolean }) {
  const row = (
    <div
      role="button"
      tabIndex={0}
      draggable
      onDragStart={(e) => setDragPayload(e, item)}
      onClick={() => !disabled && onAdd(item)}
      onKeyDown={(e) => { if (e.key === 'Enter' && !disabled) onAdd(item); }}
      className={cn(
        'group flex cursor-grab select-none items-center gap-2 rounded-md px-2 text-xs transition-colors active:cursor-grabbing',
        compact ? 'py-1' : 'py-1.5',
        'hover:bg-hover focus-visible:outline-2 focus-visible:outline-ring',
        disabled && 'opacity-60',
      )}
    >
      {icon ? <span className="flex size-6 shrink-0 items-center justify-center rounded bg-surface-2">{icon}</span> : null}
      <span className={cn('flex-1 truncate', compact ? 'text-fg-muted' : 'font-medium')}>{label}</span>
      {trailing}
      <GripVertical className="size-3.5 shrink-0 text-fg-subtle opacity-0 group-hover:opacity-100" />
    </div>
  );
  return hint ? <Tooltip content={hint} side="right">{row}</Tooltip> : row;
}
