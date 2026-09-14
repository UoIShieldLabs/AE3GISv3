import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { Building2, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Tooltip } from '@/ui';
import type { SiteNode as SiteNodeType } from '../projection';
import { NODE_SIZE } from '../constants';
import { useZoomLevel } from '../useZoomLevel';
import { useCanvasActions } from '../CanvasContext';
import { nodeCardClass } from './nodeStyles';
import { NodeHandles } from './NodeHandles';
import { NodeActions } from './NodeActions';

export const SiteNode = memo(function SiteNode({ id, data, selected, dragging }: NodeProps<SiteNodeType>) {
  const { site, subnetCount, containerCount } = data;
  const zoom = useZoomLevel();
  const a = useCanvasActions();
  const compact = zoom !== 'full';

  return (
    <div
      className={nodeCardClass(selected, cn('flex-col overflow-hidden', dragging && 'shadow-lg'))}
      style={{ width: NODE_SIZE.site.width, height: NODE_SIZE.site.height }}
      data-testid={`node-${id}`}
    >
      <NodeActions id={id} visible={!!selected && !dragging} drill expandable expanded={false} />
      <NodeHandles />

      <div className="flex items-center gap-2.5 px-3 pt-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
          <Building2 className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className={cn('truncate font-semibold', compact ? 'text-sm' : 'text-[13px]')} title={site.name}>
            {site.name}
          </div>
          {!compact ? <div className="truncate text-2xs text-fg-muted">{site.location || 'No location'}</div> : null}
        </div>
        {!compact ? (
          <Tooltip content="Expand in place" shortcut="E" side="top">
            <button
              type="button"
              className="nodrag -mr-1 self-start rounded p-1 text-fg-subtle opacity-0 transition-opacity hover:bg-hover hover:text-fg group-hover/node:opacity-100"
              onClick={(e) => { e.stopPropagation(); a.toggleExpand(id); }}
              aria-label="Expand site in place"
            >
              <ChevronsUpDown className="size-3.5" />
            </button>
          </Tooltip>
        ) : null}
      </div>

      {!compact ? (
        <div className="mt-auto flex items-center gap-3 border-t border-border bg-surface-2/60 px-3 py-1.5 text-2xs text-fg-muted">
          <span>{subnetCount} subnet{subnetCount === 1 ? '' : 's'}</span>
          <span>{containerCount} device{containerCount === 1 ? '' : 's'}</span>
        </div>
      ) : null}
    </div>
  );
});
