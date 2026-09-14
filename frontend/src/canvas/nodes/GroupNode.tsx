import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { ArrowDownRight, Building2, Minimize2, Network } from 'lucide-react';
import { cn } from '@/lib/cn';
import { IconButton } from '@/ui';
import type { GroupNode as GroupNodeType } from '../projection';
import { GROUP_HEADER } from '../constants';
import { useCanvasActions } from '../CanvasContext';
import { NodeHandles } from './NodeHandles';
import { NodeActions } from './NodeActions';

/** An expanded site or subnet: a labelled container whose children are real nodes. */
export const GroupNode = memo(function GroupNode({ id, data, selected, dragging }: NodeProps<GroupNodeType>) {
  const a = useCanvasActions();
  const isSite = data.entity === 'site';
  const Icon = isSite ? Building2 : Network;

  return (
    <div
      className={cn(
        'group/node relative h-full w-full rounded-xl border border-dashed transition-colors',
        isSite ? 'bg-accent/[0.04]' : 'bg-info/[0.05]',
        selected ? 'border-accent ring-2 ring-accent/20' : isSite ? 'border-accent/40 hover:border-accent/70' : 'border-info/40 hover:border-info/70',
      )}
      style={{ width: data.width, height: data.height }}
      data-testid={`node-${id}`}
    >
      <NodeActions id={id} visible={!!selected && !dragging} drill expandable expanded />
      <NodeHandles />
      <div
        className="flex items-center gap-2 rounded-t-xl px-3 text-[13px]"
        style={{ height: GROUP_HEADER }}
      >
        <Icon className={cn('size-4 shrink-0', isSite ? 'text-accent' : 'text-info')} />
        <span className="truncate font-semibold">{data.title}</span>
        {data.subtitle ? <span className="truncate font-mono text-2xs text-fg-muted">{data.subtitle}</span> : null}
        <span className="ml-auto flex items-center gap-0.5 opacity-0 transition-opacity group-hover/node:opacity-100">
          <IconButton label="Open" size="icon-xs" side="top" className="nodrag" onClick={() => a.drillInto(id)}>
            <ArrowDownRight />
          </IconButton>
          <IconButton label="Collapse" shortcut="E" size="icon-xs" side="top" className="nodrag" onClick={() => a.toggleExpand(id)}>
            <Minimize2 />
          </IconButton>
        </span>
      </div>
    </div>
  );
});
