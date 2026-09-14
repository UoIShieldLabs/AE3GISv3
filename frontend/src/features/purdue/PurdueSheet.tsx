import { useMemo, useState } from 'react';
import type { Container } from '@/types/topology';
import { useAppStore } from '@/store';
import { colorFor, labelFor, purdueLevelFor } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import { cn } from '@/lib/cn';
import { Select, Sheet } from '@/ui';

const LEVELS = [
  { level: 5, label: 'Level 5', name: 'Enterprise network', zone: 'IT' },
  { level: 4, label: 'Level 4', name: 'Business planning & logistics', zone: 'IT' },
  { level: 3.5, label: 'DMZ', name: 'Demilitarized zone', zone: 'DMZ' },
  { level: 3, label: 'Level 3', name: 'Operations management', zone: 'OT' },
  { level: 2, label: 'Level 2', name: 'Control (SCADA / HMI)', zone: 'OT' },
  { level: 1, label: 'Level 1', name: 'Field control (PLC / RTU)', zone: 'OT' },
  { level: 0, label: 'Level 0', name: 'Physical process', zone: 'OT' },
] as const;

const ZONE_CLASS: Record<string, string> = { IT: 'text-accent border-accent/40', DMZ: 'text-danger border-danger/40', OT: 'text-success border-success/40' };

/** Devices of a site arranged by Purdue level (levels come from the catalog). */
export function PurdueSheet() {
  const open = useAppStore((s) => s.purdueOpen);
  const setOpen = useAppStore((s) => s.setPurdueOpen);
  const topology = useAppStore((s) => s.topology);
  const [siteId, setSiteId] = useState<string | undefined>(undefined);
  const site = topology.sites.find((s) => s.id === siteId) ?? topology.sites[0];

  const byLevel = useMemo(() => {
    const map = new Map<number, { container: Container; subnet: string }[]>();
    for (const l of LEVELS) map.set(l.level, []);
    if (!site) return map;
    for (const subnet of site.subnets) {
      for (const c of subnet.containers) {
        const level = purdueLevelFor(c.type) ?? 4;
        (map.get(level) ?? map.set(level, []).get(level)!).push({ container: c, subnet: subnet.name });
      }
    }
    return map;
  }, [site]);

  return (
    <Sheet
      open={open}
      onOpenChange={setOpen}
      side="full"
      title="Purdue model"
      description="Devices grouped by the level their catalog type declares."
      headerAction={
        topology.sites.length > 1 ? (
          <Select value={site?.id} onValueChange={setSiteId} options={topology.sites.map((s) => ({ value: s.id, label: s.name }))} className="h-7 w-48 text-xs" size="sm" />
        ) : null
      }
      flush
    >
      {!site ? (
        <p className="p-6 text-center text-xs text-fg-muted">Add a site to see its Purdue view.</p>
      ) : (
        <div className="flex flex-col">
          {LEVELS.map((l, i) => {
            const items = byLevel.get(l.level) ?? [];
            const showZone = i === 0 || LEVELS[i - 1].zone !== l.zone;
            return (
              <div key={l.level} className={cn('grid grid-cols-[64px_160px_1fr] border-b border-border', showZone && 'border-t-2')}>
                <div className={cn('flex items-start justify-center border-r px-2 py-3 text-2xs font-bold', ZONE_CLASS[l.zone])}>{showZone ? l.zone : ''}</div>
                <div className="border-r border-border px-3 py-3">
                  <div className="text-xs font-semibold">{l.label}</div>
                  <div className="text-2xs text-fg-muted">{l.name}</div>
                </div>
                <div className="flex min-h-14 flex-wrap gap-2 p-2">
                  {items.length === 0 ? <span className="self-center px-2 text-2xs text-fg-subtle">—</span> : null}
                  {items.map(({ container, subnet }) => {
                    const color = colorFor(container.type);
                    return (
                      <div key={container.id} className="flex w-44 items-center gap-2 rounded-lg border border-border bg-surface px-2 py-1.5 shadow-sm">
                        <span className="flex size-7 shrink-0 items-center justify-center rounded-md" style={{ background: `color-mix(in srgb, ${color} 14%, transparent)` }}>
                          <NodeGlyph type={container.type} size={16} color={color} />
                        </span>
                        <span className="min-w-0 flex-1 leading-tight">
                          <span className="block truncate text-xs font-medium">{container.name}</span>
                          <span className="block truncate font-mono text-2xs text-fg-muted">{container.ip} · {subnet}</span>
                        </span>
                        <span className="text-2xs font-semibold" style={{ color }}>{labelFor(container.type)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Sheet>
  );
}
