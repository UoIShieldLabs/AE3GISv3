import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { Activity, Radio } from 'lucide-react';
import { colorFor, labelFor } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import { cn } from '@/lib/cn';
import { useAppStore } from '@/store';
import { effectsFor } from '@/app/themes';
import { Tooltip } from '@/ui';
import type { DeviceNode as DeviceNodeType } from '../projection';
import { NODE_SIZE } from '../constants';
import { useZoomLevel } from '../useZoomLevel';
import { nodeCardClass } from './nodeStyles';
import { NodeHandles } from './NodeHandles';
import { NodeActions } from './NodeActions';
import { useDecrypt } from './useDecrypt';

const STATUS_CLASS = {
  running: 'bg-success shadow-[0_0_0_2px_var(--success-soft)]',
  stopped: 'bg-danger',
  paused: 'bg-warning',
} as const;

export const DeviceNode = memo(function DeviceNode({ id, data, selected, dragging }: NodeProps<DeviceNodeType>) {
  const { container, status, isGateway, captureJobId, traffic, legs, guest, busy } = data;
  // colorFor/labelFor read the catalog's lookup maps: re-render when it changes
  // (a registry sync can add the type a placed node uses).
  useAppStore((s) => s.catalog);
  const color = colorFor(container.type);
  const zoom = useZoomLevel();
  const compact = zoom !== 'full';
  // A theme may have the selected node's name and IP decrypt into view.
  const decrypt = useAppStore((s) => !!effectsFor(s.theme).decrypt) && !!selected && !dragging;
  const name = useDecrypt(container.name, decrypt);
  const ip = useDecrypt((guest ? guest.ip : container.ip) || 'no ip', decrypt);

  return (
    <div
      className={nodeCardClass(selected, cn('items-center gap-2.5 px-2.5', dragging && 'shadow-lg', guest && 'border-dashed opacity-80'))}
      style={{
        width: NODE_SIZE.device.width,
        height: NODE_SIZE.device.height,
        // Something runs here: a steady ring in the node's tutorial colour
        // (selection keeps its own ring).
        ...(busy && !selected ? { borderColor: busy.color, boxShadow: `0 0 0 2px color-mix(in srgb, ${busy.color} 30%, transparent)` } : null),
      }}
      data-testid={`node-${id}`}
      data-node-type={container.type}
      data-capturing={captureJobId ? '' : undefined}
      data-busy={busy ? '' : undefined}
    >
      {/* A guest is edited (or deleted) in its own subnet, not from here. */}
      <NodeActions id={id} visible={!!selected && !dragging && !guest} container={container} />
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
            {name}
          </span>
          {!compact ? (
            <span className="ae-node-tag ml-auto shrink-0 text-2xs font-semibold tracking-wide" style={{ color }}>
              {labelFor(container.type)}
            </span>
          ) : null}
        </div>
        {!compact ? (
          <div className="flex items-center gap-1.5">
            <span className={cn('font-mono text-2xs text-fg-muted', guest ? 'shrink-0' : 'truncate')}>{ip}</span>
            {isGateway ? <span className="shrink-0 rounded-sm bg-surface-2 px-1 text-2xs font-medium text-fg-muted">GW</span> : null}
            {guest ? (
              <Tooltip content={`Lives in ${guest.homeSubnet} (${container.ip}); joins this subnet through an interface leg`} side="bottom">
                <span className="min-w-0 truncate text-2xs text-fg-subtle">via {guest.homeSubnet}</span>
              </Tooltip>
            ) : legs?.length ? (
              <Tooltip content={legs.map((l) => `${l.subnet}: ${l.ip}`).join(' · ')} side="bottom">
                <span className="shrink-0 rounded-sm bg-warning-soft px-1 text-2xs font-medium text-warning" aria-label={`${legs.length} more interface${legs.length === 1 ? '' : 's'}`}>
                  +{legs.length}
                </span>
              </Tooltip>
            ) : null}
          </div>
        ) : null}
      </div>

      {busy && !compact ? (
        <Tooltip content={<span className="flex max-w-80 flex-col gap-0.5 font-mono text-2xs">{busy.detail.map((line, i) => <span key={i} className="truncate">{line}</span>)}</span>} side="bottom">
          <span
            className="ae-node-busy absolute -bottom-2 left-2 flex max-w-[70%] items-center gap-1 rounded-sm border border-border bg-surface px-1 text-2xs leading-4 text-fg-muted"
            aria-label={`running: ${busy.detail.join('; ')}`}
          >
            <span className="size-1.5 shrink-0 rounded-full" style={{ backgroundColor: busy.color }} aria-hidden />
            <span className="truncate">{busy.label}</span>
          </span>
        </Tooltip>
      ) : null}
      {captureJobId || traffic ? (
        <div className="absolute bottom-1 right-1.5 flex items-center gap-1">
          {captureJobId ? (
            <Tooltip content="A capture runs here" side="bottom">
              <Radio className="size-3 text-danger" aria-label="capturing" />
            </Tooltip>
          ) : null}
          {traffic ? (
            <Tooltip content="Generating traffic" side="bottom">
              <Activity className="size-3 animate-pulse text-accent" aria-label="traffic" />
            </Tooltip>
          ) : null}
        </div>
      ) : null}
      {status ? (
        <Tooltip content={status[0].toUpperCase() + status.slice(1)} side="top">
          <span className={cn('absolute right-1.5 top-1.5 size-2 rounded-full', STATUS_CLASS[status])} />
        </Tooltip>
      ) : null}
    </div>
  );
});
