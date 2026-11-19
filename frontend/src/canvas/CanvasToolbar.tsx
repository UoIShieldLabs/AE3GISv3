import { useMemo } from 'react';
import { Panel, useReactFlow } from '@xyflow/react';
import { Cable, ChevronDown, Grid3X3, Hand, LayoutGrid, ListPlus, Map as MapIcon, Maximize, Maximize2, Minimize2, MousePointer2, Plus } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { LAYOUT_MODES, currentLayout, lastLayout, type LayoutMode } from './layout';
import { colorFor } from '@/catalog/catalog';
import { useCatalogTree } from '@/catalog/useCatalogTree';
import { NodeGlyph } from '@/catalog/icons';
import type { Scope } from '@/lib/topology';
import {
  Button, IconButton, Separator,
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem,
  DropdownMenuSeparator, DropdownMenuSub, DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuTrigger,
} from '@/ui';
import type { PaletteItem } from './interactions/dnd';

export interface CanvasToolbarProps {
  scope: Scope;
  readOnly?: boolean;
  onAdd: (item: PaletteItem) => void;
  onBulkDevices?: () => void;
  onBulkConnections?: () => void;
  /** Lay the scope out with this algorithm (picking a layout applies it). */
  onApplyLayout: (mode: LayoutMode) => void;
  expandableCount: number;
  expandedCount: number;
  onExpandAll: () => void;
  onCollapseAll: () => void;
}

export function CanvasToolbar({ scope, readOnly, onAdd, onBulkDevices, onBulkConnections, onApplyLayout, expandableCount, expandedCount, onExpandAll, onCollapseAll }: CanvasToolbarProps) {
  const { fitView } = useReactFlow();
  const tree = useCatalogTree();
  const { tool, snapToGrid, showMinimap, layoutMode, topology } = useAppShallow((s) => ({
    tool: s.tool, snapToGrid: s.snapToGrid, showMinimap: s.showMinimap, layoutMode: s.layoutMode, topology: s.topology,
  }));
  const layout = useMemo(() => currentLayout(topology, scope), [topology, scope]);
  const relayout = lastLayout(topology, scope) ?? layoutMode;
  const { setTool, setSnapToGrid, setShowMinimap } = useAppStore.getState();
  const layoutLabel = LAYOUT_MODES.find((m) => m.value === layout)?.label ?? 'Custom';

  const addLabel = scope.level === 'root' ? 'Site' : scope.level === 'site' ? 'Subnet' : 'Device';

  return (
    <Panel position="top-left" className="!m-3">
      <div className="flex items-center gap-1 rounded-lg border border-border bg-surface p-1 shadow-md">
        {!readOnly ? (
          <>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="primary" size="sm">
                  <Plus /> {addLabel} <ChevronDown className="-mr-1 opacity-70" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                {scope.level === 'root' ? (
                  <DropdownMenuItem onSelect={() => onAdd({ kind: 'site' })}>Site…</DropdownMenuItem>
                ) : null}
                {scope.level !== 'subnet' ? (
                  <DropdownMenuItem disabled={scope.level === 'root'} onSelect={() => onAdd({ kind: 'subnet' })}>Subnet…</DropdownMenuItem>
                ) : null}
                {scope.level !== 'root' ? (
                  <>
                    {scope.level === 'site' ? <DropdownMenuSeparator /> : null}
                    <DropdownMenuLabel>Devices</DropdownMenuLabel>
                    {tree.map((cat) => (
                      <DropdownMenuSub key={cat.id}>
                        <DropdownMenuSubTrigger>{cat.label}</DropdownMenuSubTrigger>
                        <DropdownMenuSubContent>
                          {cat.types.map(({ type, name }) => (
                            <DropdownMenuItem key={type} onSelect={() => onAdd({ kind: 'device', type })}>
                              <NodeGlyph type={type} size={14} color={colorFor(type)} />
                              {name}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuSubContent>
                      </DropdownMenuSub>
                    ))}
                  </>
                ) : null}
                {onBulkDevices || onBulkConnections ? <DropdownMenuSeparator /> : null}
                {onBulkDevices ? <DropdownMenuItem onSelect={onBulkDevices}><ListPlus /> Bulk add devices…</DropdownMenuItem> : null}
                {onBulkConnections ? <DropdownMenuItem onSelect={onBulkConnections}><Cable /> Bulk connections…</DropdownMenuItem> : null}
              </DropdownMenuContent>
            </DropdownMenu>
            <Separator orientation="vertical" className="mx-0.5 h-5" />
          </>
        ) : null}

        <IconButton label="Select" shortcut="V" size="icon-sm" variant={tool === 'select' ? 'secondary' : 'ghost'} onClick={() => setTool('select')}>
          <MousePointer2 />
        </IconButton>
        <IconButton label="Pan" shortcut="H" size="icon-sm" variant={tool === 'pan' ? 'secondary' : 'ghost'} onClick={() => setTool('pan')}>
          <Hand />
        </IconButton>
        <Separator orientation="vertical" className="mx-0.5 h-5" />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <LayoutGrid /> Layout: <span className="text-fg-muted">{layoutLabel}</span> <ChevronDown className="-mr-1 opacity-70" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            {/* Picking a layout applies it; picking the current one tidies the scope up again. */}
            <DropdownMenuRadioGroup value={layout}>
              {LAYOUT_MODES.map((m) => (
                <DropdownMenuRadioItem key={m.value} value={m.value} disabled={readOnly} onSelect={() => onApplyLayout(m.value)} shortcut={m.value === relayout && !readOnly ? 'L' : undefined}>
                  {m.label}
                </DropdownMenuRadioItem>
              ))}
              <DropdownMenuSeparator />
              {/* A status, not an action: a scope reads as Custom once anything in it is moved by hand. */}
              <DropdownMenuRadioItem value="custom" disabled className="data-[state=checked]:opacity-100">
                Custom
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        <IconButton label="Fit to view" shortcut="F" size="icon-sm" onClick={() => void fitView({ padding: 0.2, maxZoom: 1.25, duration: 200 })}>
          <Maximize />
        </IconButton>
        <IconButton label={snapToGrid ? 'Snap to grid: on' : 'Snap to grid: off'} size="icon-sm" variant={snapToGrid ? 'secondary' : 'ghost'} onClick={() => setSnapToGrid(!snapToGrid)}>
          <Grid3X3 />
        </IconButton>
        <IconButton label={showMinimap ? 'Hide minimap' : 'Show minimap'} size="icon-sm" variant={showMinimap ? 'secondary' : 'ghost'} onClick={() => setShowMinimap(!showMinimap)}>
          <MapIcon />
        </IconButton>

        {expandableCount > 0 ? (
          <>
            <Separator orientation="vertical" className="mx-0.5 h-5" />
            {expandedCount < expandableCount ? (
              <IconButton label="Expand all in place" size="icon-sm" onClick={onExpandAll}><Maximize2 /></IconButton>
            ) : null}
            {expandedCount > 0 ? (
              <IconButton label="Collapse all" size="icon-sm" onClick={onCollapseAll}><Minimize2 /></IconButton>
            ) : null}
          </>
        ) : null}
      </div>
    </Panel>
  );
}
