import { NodeToolbar, Position } from '@xyflow/react';
import { ArrowDownRight, Copy, Maximize2, Minimize2, Terminal, Trash2 } from 'lucide-react';
import { IconButton } from '@/ui';
import { useCanvasActions } from '../CanvasContext';
import type { Container } from '@/types/topology';

export interface NodeActionsProps {
  id: string;
  visible: boolean;
  drill?: boolean;
  expandable?: boolean;
  expanded?: boolean;
  container?: Container;
}

/** Floating quick actions above a selected node. */
export function NodeActions({ id, visible, drill, expandable, expanded, container }: NodeActionsProps) {
  const a = useCanvasActions();
  return (
    <NodeToolbar isVisible={visible} position={Position.Top} offset={8} className="nodrag nopan">
      {drill ? (
        <IconButton label="Open" shortcut="Enter" size="icon-sm" side="top" onClick={() => a.drillInto(id)}>
          <ArrowDownRight />
        </IconButton>
      ) : null}
      {expandable ? (
        <IconButton label={expanded ? 'Collapse' : 'Expand in place'} shortcut="E" size="icon-sm" side="top" onClick={() => a.toggleExpand(id)}>
          {expanded ? <Minimize2 /> : <Maximize2 />}
        </IconButton>
      ) : null}
      {container ? (
        <IconButton
          label={a.canOpenTerminal ? 'Open terminal' : 'Deploy to open a terminal'}
          size="icon-sm"
          side="top"
          disabled={!a.canOpenTerminal}
          onClick={() => a.openTerminal(container)}
        >
          <Terminal />
        </IconButton>
      ) : null}
      {!a.readOnly ? (
        <>
          <IconButton label="Duplicate" shortcut="⌘D" size="icon-sm" side="top" onClick={() => a.duplicate([id])}>
            <Copy />
          </IconButton>
          <IconButton label="Delete" shortcut="⌫" size="icon-sm" side="top" className="hover:text-danger" onClick={() => a.remove([id])}>
            <Trash2 />
          </IconButton>
        </>
      ) : null}
    </NodeToolbar>
  );
}
