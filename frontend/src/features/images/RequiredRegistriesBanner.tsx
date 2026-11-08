import { useMemo, useState } from 'react';
import { Boxes, Plus, X } from 'lucide-react';
import { useAppStore } from '@/store';
import { useCan } from '@/lib/permissions';
import { Button, IconButton } from '@/ui';
import { addRegistry } from './actions';
import { requiredRegistries } from './requiredRegistries';

/** Prompt to add the Docker Hub registries a just-imported scenario needs, so
 *  its `tollan/*` node types resolve and its images can pull. */
export function RequiredRegistriesBanner() {
  const topology = useAppStore((s) => s.topology);
  const report = useAppStore((s) => s.images);
  const [dismissed, setDismissed] = useState('');
  const [adding, setAdding] = useState(false);
  const manage = useCan('manageImages');

  const missing = useMemo(
    () => requiredRegistries(topology, (report?.registries ?? []).map((r) => r.namespace)),
    [topology, report],
  );
  const signature = missing.map((m) => m.namespace).join(',');
  if (!missing.length || dismissed === signature) return null;

  const addAll = async () => {
    setAdding(true);
    try {
      for (const m of missing) await addRegistry(m.url);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="flex items-center gap-2 border-b border-border bg-info-soft px-3 py-1.5 text-xs text-info" role="status">
      <Boxes className="size-3.5 shrink-0" />
      <span className="min-w-0 flex-1 truncate">
        This scenario uses images from Docker Hub {missing.length === 1 ? 'namespace' : 'namespaces'}{' '}
        <span className="font-mono">{missing.map((m) => m.namespace).join(', ')}</span> — not added yet.
      </span>
      {manage ? (
        <Button size="xs" variant="ghost" loading={adding} onClick={() => void addAll()}><Plus /> Add &amp; sync</Button>
      ) : (
        <span className="shrink-0">Ask your instructor to add {missing.length === 1 ? 'it' : 'them'}.</span>
      )}
      <IconButton label="Dismiss" size="icon-xs" onClick={() => setDismissed(signature)}><X /></IconButton>
    </div>
  );
}
