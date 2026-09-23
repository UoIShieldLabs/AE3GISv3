import { Hammer, Layers, RefreshCw } from 'lucide-react';
import { effectiveImage } from '@/catalog/catalog';
import { useAppStore } from '@/store';
import { Button } from '@/ui';
import { buildImages } from './actions';
import { ImageStatusBadge } from './ImageStatusBadge';
import { useImageStatus } from './status';

/** Build status of a container's image, with the action that fixes it. */
export function ImageStatusLine({ container }: { container: { type: string; image?: string } }) {
  const ref = effectiveImage(container);
  const img = useImageStatus(ref);
  const openImages = useAppStore((s) => s.openImages);
  if (!img || img.kind !== 'build') return null;
  const action =
    img.status === 'missing' || img.status === 'failed'
      ? { label: 'Build now', icon: <Hammer />, run: () => void buildImages([ref]) }
      : img.status === 'stale' || img.status === 'unmanaged'
        ? { label: 'Rebuild', icon: <RefreshCw />, run: () => void buildImages([ref]) }
        : null;
  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-border bg-surface-2/50 p-2">
      <div className="flex items-center gap-2">
        <ImageStatusBadge image={img} />
        <div className="ml-auto flex items-center gap-1">
          {action ? <Button size="xs" variant="secondary" onClick={action.run}>{action.icon} {action.label}</Button> : null}
          <Button size="xs" variant="ghost" onClick={() => openImages(ref)}><Layers /> Images</Button>
        </div>
      </div>
      <p className="text-2xs text-fg-subtle">{img.reason}</p>
    </div>
  );
}
