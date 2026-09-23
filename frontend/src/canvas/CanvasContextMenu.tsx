import { ArrowDownRight, Cable, Copy, ListPlus, Maximize2, Minimize2, MousePointerSquareDashed, Plus, Sparkles, Terminal, Trash2, Maximize } from 'lucide-react';
import { useReactFlow } from '@xyflow/react';
import type { Position } from '@/types/topology';
import type { Scope } from '@/lib/topology';
import { colorFor } from '@/catalog/catalog';
import { useCatalogTree } from '@/catalog/useCatalogTree';
import { NodeGlyph } from '@/catalog/icons';
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuLabel, ContextMenuSeparator, ContextMenuSub,
  ContextMenuSubContent, ContextMenuSubTrigger, ContextMenuTrigger,
} from '@/ui';
import type { PaletteItem } from './interactions/dnd';
import type { CanvasNode } from './projection';

export type ContextTarget =
  | { kind: 'pane'; flowPosition: Position }
  | { kind: 'node'; node: CanvasNode }
  | { kind: 'edge'; id: string }
  | { kind: 'selection'; nodeIds: string[] };

export interface CanvasContextMenuProps {
  scope: Scope;
  target: ContextTarget | null;
  readOnly?: boolean;
  isExpanded: (id: string) => boolean;
  canOpenTerminal: boolean;
  children: React.ReactNode;
  onAdd: (item: PaletteItem, at?: Position) => void;
  onDrill: (id: string) => void;
  onToggleExpand: (id: string) => void;
  onTerminal: (nodeId: string) => void;
  onDuplicate: (ids: string[]) => void;
  onDelete: (nodeIds: string[], edgeIds: string[]) => void;
  onSelectAll: () => void;
  onAutoLayout: () => void;
  onBulkDevices?: () => void;
  onBulkConnections?: () => void;
}

export function CanvasContextMenu({
  scope, target, readOnly, isExpanded, canOpenTerminal, children,
  onAdd, onDrill, onToggleExpand, onTerminal, onDuplicate, onDelete, onSelectAll, onAutoLayout, onBulkDevices, onBulkConnections,
}: CanvasContextMenuProps) {
  const { fitView } = useReactFlow();
  const tree = useCatalogTree();

  const addItems = (at?: Position) => {
    const items: React.ReactNode[] = [];
    if (scope.level === 'root') items.push(<ContextMenuItem key="site" onSelect={() => onAdd({ kind: 'site' }, at)}><Plus /> Add site…</ContextMenuItem>);
    if (scope.level === 'site') items.push(<ContextMenuItem key="subnet" onSelect={() => onAdd({ kind: 'subnet' }, at)}><Plus /> Add subnet…</ContextMenuItem>);
    if (scope.level === 'subnet') {
      items.push(
        <ContextMenuSub key="device">
          <ContextMenuSubTrigger><Plus /> Add device</ContextMenuSubTrigger>
          <ContextMenuSubContent>
            {tree.map((cat) => (
              <ContextMenuSub key={cat.id}>
                <ContextMenuSubTrigger>{cat.label}</ContextMenuSubTrigger>
                <ContextMenuSubContent>
                  {cat.types.map(({ type, name }) => (
                    <ContextMenuItem key={type} onSelect={() => onAdd({ kind: 'device', type }, at)}>
                      <NodeGlyph type={type} size={14} color={colorFor(type)} />
                      {name}
                    </ContextMenuItem>
                  ))}
                </ContextMenuSubContent>
              </ContextMenuSub>
            ))}
          </ContextMenuSubContent>
        </ContextMenuSub>,
      );
    }
    return items;
  };

  let content: React.ReactNode = null;
  if (target?.kind === 'pane') {
    content = (
      <>
        {!readOnly ? addItems(target.flowPosition) : null}
        {!readOnly && onBulkDevices ? <ContextMenuItem onSelect={onBulkDevices}><ListPlus /> Bulk add devices…</ContextMenuItem> : null}
        {!readOnly && onBulkConnections ? <ContextMenuItem onSelect={onBulkConnections}><Cable /> Bulk connections…</ContextMenuItem> : null}
        {!readOnly ? <ContextMenuSeparator /> : null}
        <ContextMenuItem onSelect={onSelectAll} shortcut="⌘A"><MousePointerSquareDashed /> Select all</ContextMenuItem>
        <ContextMenuItem onSelect={() => void fitView({ padding: 0.2, maxZoom: 1.25, duration: 200 })} shortcut="F"><Maximize /> Fit to view</ContextMenuItem>
        {!readOnly ? <ContextMenuItem onSelect={onAutoLayout} shortcut="L"><Sparkles /> Apply layout</ContextMenuItem> : null}
      </>
    );
  } else if (target?.kind === 'node') {
    const n = target.node;
    const isContainerNode = n.type === 'device';
    const expandable = n.type === 'site' || n.type === 'subnet' || n.type === 'group';
    const expanded = isExpanded(n.id);
    content = (
      <>
        <ContextMenuLabel className="truncate normal-case tracking-normal">
          {n.type === 'device' ? n.data.container.name : n.type === 'site' ? n.data.site.name : n.type === 'subnet' ? n.data.subnet.name : n.data.title}
        </ContextMenuLabel>
        {!isContainerNode ? <ContextMenuItem onSelect={() => onDrill(n.id)} shortcut="↵"><ArrowDownRight /> Open</ContextMenuItem> : null}
        {expandable ? (
          <ContextMenuItem onSelect={() => onToggleExpand(n.id)} shortcut="E">
            {expanded ? <Minimize2 /> : <Maximize2 />} {expanded ? 'Collapse' : 'Expand in place'}
          </ContextMenuItem>
        ) : null}
        {isContainerNode ? (
          <ContextMenuItem onSelect={() => onTerminal(n.id)} disabled={!canOpenTerminal}><Terminal /> Open terminal</ContextMenuItem>
        ) : null}
        {!readOnly ? (
          <>
            <ContextMenuSeparator />
            <ContextMenuItem onSelect={() => onDuplicate([n.id])} shortcut="⌘D"><Copy /> Duplicate</ContextMenuItem>
            <ContextMenuItem variant="danger" onSelect={() => onDelete([n.id], [])} shortcut="⌫"><Trash2 /> Delete</ContextMenuItem>
          </>
        ) : null}
      </>
    );
  } else if (target?.kind === 'edge') {
    content = !readOnly ? (
      <ContextMenuItem variant="danger" onSelect={() => onDelete([], [target.id])} shortcut="⌫"><Trash2 /> Delete connection</ContextMenuItem>
    ) : (
      <ContextMenuLabel>Connection</ContextMenuLabel>
    );
  } else if (target?.kind === 'selection') {
    content = (
      <>
        <ContextMenuLabel>{target.nodeIds.length} selected</ContextMenuLabel>
        {!readOnly ? (
          <>
            <ContextMenuItem onSelect={() => onDuplicate(target.nodeIds)} shortcut="⌘D"><Copy /> Duplicate</ContextMenuItem>
            <ContextMenuItem variant="danger" onSelect={() => onDelete(target.nodeIds, [])} shortcut="⌫"><Trash2 /> Delete</ContextMenuItem>
          </>
        ) : null}
      </>
    );
  }

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="min-w-52">{content}</ContextMenuContent>
    </ContextMenu>
  );
}
