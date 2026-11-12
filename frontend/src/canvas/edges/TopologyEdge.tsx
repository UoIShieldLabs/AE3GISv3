import { memo } from 'react';
import { BaseEdge, EdgeLabelRenderer, getStraightPath, useInternalNode, type EdgeProps } from '@xyflow/react';
import { Radio } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Tooltip } from '@/ui';
import { openCaptureTab } from '@/features/capture/actions';
import type { CanvasEdge, EdgeVariant } from '../projection';
import { floatingEdgeParams } from './geometry';

// A line is solid unless it carries traffic: dashes are kept for that, so a
// variant shows through colour and width only.
const VARIANT: Record<EdgeVariant, { className: string; width: number }> = {
  link: { className: 'stroke-fg-subtle', width: 1.5 },
  uplink: { className: 'stroke-fg-muted', width: 1.75 },
  wan: { className: 'stroke-accent', width: 1.75 },
  site: { className: 'stroke-accent', width: 2.25 },
  attachment: { className: 'stroke-warning', width: 1.5 },
};
/** Dashes of a link carrying traffic; `ae-dash` moves them by two periods. */
const TRAFFIC_DASH = '6 4';

export const TopologyEdge = memo(function TopologyEdge({ id, source, target, data, selected }: EdgeProps<CanvasEdge>) {
  const sourceNode = useInternalNode(source);
  const targetNode = useInternalNode(target);
  if (!sourceNode || !targetNode) return null;

  const { sx, sy, tx, ty } = floatingEdgeParams(sourceNode, targetNode);
  const [path, labelX, labelY] = getStraightPath({ sourceX: sx, sourceY: sy, targetX: tx, targetY: ty });
  const variant = VARIANT[data?.variant ?? 'link'];
  const traffic = data?.traffic;

  return (
    <>
      {selected ? <BaseEdge id={`${id}-halo`} path={path} className="!stroke-accent/25" style={{ strokeWidth: variant.width + 6 }} interactionWidth={0} /> : null}
      <BaseEdge
        id={id}
        path={path}
        className={cn(
          'transition-[stroke] duration-100',
          selected ? '!stroke-accent' : variant.className,
          // The dashes crawl the way the traffic flows (both ways: along the edge).
          traffic && 'edge-traffic',
          traffic === 'rev' && 'edge-traffic-rev',
        )}
        style={{
          strokeWidth: selected ? variant.width + 0.75 : variant.width,
          strokeDasharray: traffic ? TRAFFIC_DASH : undefined,
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
