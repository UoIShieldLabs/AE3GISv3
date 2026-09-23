import { useMemo, useState } from 'react';
import { AlertTriangle, Hammer, Info, Layers, RefreshCw, X } from 'lucide-react';
import { effectiveImage } from '@/catalog/catalog';
import { cn } from '@/lib/cn';
import { useAppStore } from '@/store';
import { Button, IconButton, Spinner } from '@/ui';
import { buildImages } from './actions';
import { classifyRequired, nameList, requiredImageRefs } from './required';

type Tone = 'info' | 'warning' | 'danger';
const TONE: Record<Tone, string> = { info: 'bg-info-soft text-info', warning: 'bg-warning-soft text-warning', danger: 'bg-danger-soft text-danger' };

/** What this topology's images still need before (or since) a deploy. */
export function RequiredImagesBanner() {
  const topology = useAppStore((s) => s.topology);
  const report = useAppStore((s) => s.images);
  const catalog = useAppStore((s) => s.catalog);
  const openImages = useAppStore((s) => s.openImages);
  const [dismissed, setDismissed] = useState<string | null>(null);

  const req = useMemo(() => {
    void catalog; // default images resolve through the catalog
    return classifyRequired(requiredImageRefs(topology, effectiveImage), report?.images ?? []);
  }, [topology, report, catalog]);

  const rows: { key: string; tone: Tone; icon: React.ReactNode; text: string; action?: React.ReactNode }[] = [];
  if (req.unavailable.length) {
    rows.push({ key: 'unavailable', tone: 'danger', icon: <AlertTriangle />, text: `Can't build ${nameList(req.unavailable)} here: ${req.unavailable[0].reason}` });
  }
  if (req.failed.length) {
    rows.push({
      key: 'failed', tone: 'danger', icon: <AlertTriangle />, text: `${nameList(req.failed)} failed to build`,
      action: <Button size="xs" variant="ghost" onClick={() => void buildImages(req.failed.map((i) => i.ref))}><RefreshCw /> Retry</Button>,
    });
  }
  if (req.building.length) {
    rows.push({ key: 'building', tone: 'info', icon: <Spinner className="text-current" />, text: `Building ${nameList(req.building)}…` });
  }
  if (req.toBuild.length) {
    const n = req.toBuild.length;
    rows.push({
      key: 'build', tone: 'info', icon: <Info />, text: `${n} image${n === 1 ? '' : 's'} will be built on first deploy: ${nameList(req.toBuild)}`,
      action: <Button size="xs" variant="ghost" onClick={() => void buildImages(req.toBuild.map((i) => i.ref))}><Hammer /> Build now</Button>,
    });
  }
  if (req.stale.length) {
    rows.push({
      key: 'stale', tone: 'warning', icon: <RefreshCw />, text: `${nameList(req.stale)} ${req.stale.length === 1 ? 'has' : 'have'} source changes since last built`,
      action: <Button size="xs" variant="ghost" onClick={() => void buildImages(req.stale.map((i) => i.ref))}><RefreshCw /> Rebuild</Button>,
    });
  }

  const signature = rows.map((r) => `${r.key}:${r.text}`).join('|');
  if (!rows.length || dismissed === signature) return null;
  return (
    <div className="flex items-start gap-2 border-b border-border bg-surface px-2 py-1" role="status">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        {rows.map((r) => (
          <div key={r.key} className={cn('flex items-center gap-2 rounded-md px-2 py-1 text-xs [&_svg]:size-3.5 [&_svg]:shrink-0', TONE[r.tone])}>
            {r.icon}
            <span className="min-w-0 flex-1 truncate" title={r.text}>{r.text}</span>
            {r.action}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-0.5 pt-0.5">
        <Button size="xs" variant="ghost" onClick={() => openImages()}><Layers /> Images</Button>
        <IconButton label="Dismiss" size="icon-xs" onClick={() => setDismissed(signature)}><X /></IconButton>
      </div>
    </div>
  );
}
