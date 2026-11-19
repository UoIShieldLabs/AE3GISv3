import type { PresetSummary } from '@/api/client';
import { Button } from '@/ui';
import { CardGrid } from './TopologyCollection';

/** Templates: each one makes a new topology of the caller's. */
export function PresetsSection({ presets, busyId, onUse, empty }: {
  presets: PresetSummary[];
  busyId: string | null;
  onUse: (id: string) => void;
  empty: React.ReactNode;
}) {
  if (presets.length === 0) return <>{empty}</>;
  return (
    <CardGrid>
      {presets.map((p) => (
        <li key={p.id} className="flex flex-col gap-2 rounded-xl border border-border bg-surface p-4 shadow-sm">
          <div className="text-sm font-medium">{p.name}</div>
          <p className="line-clamp-3 text-xs text-fg-muted">{p.description}</p>
          <div className="mt-auto flex items-center justify-between pt-1 text-2xs text-fg-subtle">
            <span>{p.site_count} site{p.site_count === 1 ? '' : 's'} · {p.scenario_count} scenario{p.scenario_count === 1 ? '' : 's'}</span>
            <Button size="sm" onClick={() => onUse(p.id)} loading={busyId === p.id} disabled={busyId !== null}>Use preset</Button>
          </div>
        </li>
      ))}
    </CardGrid>
  );
}
