import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { ChevronsUpDown, Network } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Tooltip } from '@/ui';
import type { SubnetNode as SubnetNodeType } from '../projection';
import { NODE_SIZE } from '../constants';
import { useZoomLevel } from '../useZoomLevel';
import { useCanvasActions } from '../CanvasContext';
import { nodeCardClass } from './nodeStyles';
import { NodeHandles } from './NodeHandles';
import { NodeActions } from './NodeActions';

export const SubnetNode = memo(function SubnetNode({ id, data, selected, dragging }: NodeProps<SubnetNodeType>) {
  const { subnet, containerCount, gateway, running } = data;
  const zoom = useZoomLevel();
  const a = useCanvasActions();
  const compact = zoom !== 'full';
  const total = subnet.containers.length;

  return (
    <div
      className={nodeCardClass(selected, cn('flex-col overflow-hidden', dragging && 'shadow-lg'))}
      style={{ width: NODE_SIZE.subnet.width, height: NODE_SIZE.subnet.height }}
      data-testid={`node-${id}`}
    >
      <NodeActions id={id} visible={!!selected && !dragging} drill expandable expanded={false} />
      <NodeHandles />
      <div className="absolute inset-y-0 left-0 w-1 bg-info/70" />

      <div className="flex items-center gap-2 px-3 pt-2.5">
        <Network className="size-4 shrink-0 text-info" />
        <div className="min-w-0 flex-1">
          <div className={cn('truncate font-medium', compact ? 'text-sm' : 'text-[13px]')} title={subnet.name}>
            {subnet.name}
          </div>
          {!compact ? <div className="truncate font-mono text-2xs text-fg-muted">{subnet.cidr}</div> : null}
        </div>
        {!compact ? (
          <Tooltip content="Expand in place" shortcut="E" side="top">
            <button
              type="button"
              className="nodrag -mr-1 rounded p-1 text-fg-subtle opacity-0 transition-opacity hover:bg-hover hover:text-fg group-hover/node:opacity-100"
              onClick={(e) => { e.stopPropagation(); a.toggleExpand(id); }}
              aria-label="Expand subnet in place"
            >
              <ChevronsUpDown className="size-3.5" />
            </button>
          </Tooltip>
        ) : null}
      </div>

      {!compact ? (
        <div className="mt-auto flex items-center gap-2 border-t border-border bg-surface-2/60 px-3 py-1.5 text-2xs text-fg-muted">
          <span>{containerCount} device{containerCount === 1 ? '' : 's'}</span>
          {gateway ? <span className="truncate font-mono">gw {gateway.ip}</span> : <span className="text-warning">no gateway</span>}
          {running !== undefined ? (
            <span className={cn('ml-auto font-mono', running === total ? 'text-success' : running === 0 ? 'text-danger' : 'text-warning')}>
              {running}/{total}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
});
