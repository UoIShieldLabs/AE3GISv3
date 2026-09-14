import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { colorFor, labelFor } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import { cn } from '@/lib/cn';
import { Tooltip } from '@/ui';
import type { DeviceNode as DeviceNodeType } from '../projection';
import { NODE_SIZE } from '../constants';
import { useZoomLevel } from '../useZoomLevel';
import { nodeCardClass } from './nodeStyles';
import { NodeHandles } from './NodeHandles';
import { NodeActions } from './NodeActions';

const STATUS_CLASS = {
  running: 'bg-success shadow-[0_0_0_2px_var(--success-soft)]',
  stopped: 'bg-danger',
  paused: 'bg-warning',
} as const;

export const DeviceNode = memo(function DeviceNode({ id, data, selected, dragging }: NodeProps<DeviceNodeType>) {
  const { container, status, isGateway } = data;
  const color = colorFor(container.type);
  const zoom = useZoomLevel();
  const compact = zoom !== 'full';

  return (
    <div
      className={nodeCardClass(selected, cn('items-center gap-2.5 px-2.5', dragging && 'shadow-lg'))}
      style={{ width: NODE_SIZE.device.width, height: NODE_SIZE.device.height }}
      data-testid={`node-${id}`}
    >
      <NodeActions id={id} visible={!!selected && !dragging} container={container} />
      <NodeHandles />

      <div
        className="flex size-9 shrink-0 items-center justify-center rounded-md"
        style={{ background: `color-mix(in srgb, ${color} 14%, transparent)` }}
      >
        <NodeGlyph type={container.type} size={22} color={color} />
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-0.5 leading-tight">
        <div className="flex items-center gap-1.5 pr-3">
          <span className={cn('truncate font-medium', compact ? 'text-sm' : 'text-[13px]')} title={container.name}>
            {container.name}
          </span>
          {!compact ? (
            <span className="ml-auto shrink-0 text-2xs font-semibold tracking-wide" style={{ color }}>
              {labelFor(container.type)}
            </span>
          ) : null}
        </div>
        {!compact ? (
          <div className="flex items-center gap-1.5">
            <span className="truncate font-mono text-2xs text-fg-muted">{container.ip || 'no ip'}</span>
            {isGateway ? <span className="shrink-0 rounded bg-surface-2 px-1 text-2xs font-medium text-fg-muted">GW</span> : null}
          </div>
        ) : null}
      </div>

      {status ? (
        <Tooltip content={status[0].toUpperCase() + status.slice(1)} side="top">
          <span className={cn('absolute right-1.5 top-1.5 size-2 rounded-full', STATUS_CLASS[status])} />
        </Tooltip>
      ) : null}
    </div>
  );
});
