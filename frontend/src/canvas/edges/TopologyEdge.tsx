import { memo } from 'react';
import { BaseEdge, EdgeLabelRenderer, getStraightPath, useInternalNode, type EdgeProps } from '@xyflow/react';
import { Radio } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Tooltip } from '@/ui';
import { openCaptureTab } from '@/features/capture/actions';
import type { CanvasEdge, EdgeVariant } from '../projection';
import { floatingEdgeParams } from './geometry';

const VARIANT: Record<EdgeVariant, { className: string; width: number; dash?: string }> = {
  link: { className: 'stroke-fg-subtle', width: 1.5 },
  uplink: { className: 'stroke-fg-subtle', width: 1.5, dash: '6 4' },
  wan: { className: 'stroke-accent', width: 1.75 },
  site: { className: 'stroke-accent', width: 1.75, dash: '9 5' },
};

export const TopologyEdge = memo(function TopologyEdge({ id, source, target, data, selected }: EdgeProps<CanvasEdge>) {
  const sourceNode = useInternalNode(source);
  const targetNode = useInternalNode(target);
  if (!sourceNode || !targetNode) return null;

  const { sx, sy, tx, ty } = floatingEdgeParams(sourceNode, targetNode);
  const [path, labelX, labelY] = getStraightPath({ sourceX: sx, sourceY: sy, targetX: tx, targetY: ty });
  const variant = VARIANT[data?.variant ?? 'link'];
  const active = !!data?.active;

  return (
    <>
      {selected ? <BaseEdge id={`${id}-halo`} path={path} className="!stroke-accent/25" style={{ strokeWidth: variant.width + 6 }} interactionWidth={0} /> : null}
      <BaseEdge
        id={id}
        path={path}
        className={cn('transition-[stroke] duration-100', selected ? '!stroke-accent' : variant.className, active && 'edge-active')}
        style={{
          strokeWidth: selected ? variant.width + 0.75 : variant.width,
          strokeDasharray: active ? '6 4' : variant.dash,
        }}
        interactionWidth={16}
      />
      {data?.captureJobId ? (
        <EdgeLabelRenderer>
          <Tooltip content="Capturing: click to view" side="top">
            <button
              type="button"
              aria-label="View capture"
              onClick={() => openCaptureTab(data.captureJobId!)}
              className="nodrag nopan pointer-events-auto absolute flex items-center gap-1 rounded-full border border-danger/40 bg-surface px-1.5 py-0.5 text-2xs font-medium text-danger shadow-sm hover:bg-danger-soft"
              style={{ transform: `translate(-50%, ${data.label ? '-160%' : '-50%'}) translate(${labelX}px, ${labelY}px)` }}
            >
              <span className="size-1.5 animate-pulse rounded-full bg-danger" />
              <Radio className="size-3" aria-hidden />
            </button>
          </Tooltip>
        </EdgeLabelRenderer>
      ) : null}
      {data?.label ? (
        <EdgeLabelRenderer>
          <div
            className={cn(
              'nodrag nopan pointer-events-auto absolute rounded-md border px-1.5 py-0.5 text-2xs font-medium shadow-sm',
              selected ? 'border-accent bg-accent-soft text-accent' : 'border-border bg-surface text-fg-muted',
            )}
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
});
