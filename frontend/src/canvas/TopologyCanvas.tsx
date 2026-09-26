import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow, ReactFlowProvider, Background, BackgroundVariant, MiniMap, Controls,
  applyNodeChanges, applyEdgeChanges, useReactFlow, useNodesInitialized, useOnSelectionChange,
  SelectionMode, ConnectionMode,
  type NodeChange, type EdgeChange, type Connection, type OnNodeDrag, type NodeMouseHandler, type EdgeMouseHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Plus } from 'lucide-react';
import type { Position } from '@/types/topology';
import { locate, type Scope } from '@/lib/topology';
import { useAppStore, undo, redo } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { colorFor } from '@/catalog/catalog';
import { useResolvedTheme } from '@/app/theme';
import { Button, EmptyState, toast } from '@/ui';
import { openCaptureTab, stopCapture } from '@/features/capture/actions';
import { openTrafficPanel } from '@/features/traffic/actions';
import { activityIndex, project, expandableIds, toStoredPosition, type CanvasEdge, type CanvasNode, type GroupNodeData } from './projection';
import { nodeTypes } from './nodes';
import { edgeTypes, ConnectionLine } from './edges';
import { CanvasActionsContext, type CanvasActions } from './CanvasContext';
import { CanvasToolbar } from './CanvasToolbar';
import { CanvasContextMenu, type ContextTarget } from './CanvasContextMenu';
import { useCanvasHotkeys } from './interactions/useCanvasHotkeys';
import { readDragPayload, type PaletteItem } from './interactions/dnd';
import { GRID, NODE_SIZE } from './constants';
import { useAddEntity } from '@/features/topology/AddEntityContext';

export interface TopologyCanvasProps {
  scope: Scope;
  onNavigate: (scope: Scope) => void;
  onSave?: () => void;
  readOnly?: boolean;
}

export function TopologyCanvas(props: TopologyCanvasProps) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}

const scopeKeyOf = (s: Scope) => (s.level === 'root' ? 'root' : s.level === 'site' ? `site:${s.siteId}` : `subnet:${s.siteId}:${s.subnetId}`);

function CanvasInner({ scope, onNavigate, onSave, readOnly = false }: TopologyCanvasProps) {
  const rf = useReactFlow<CanvasNode, CanvasEdge>();
  const theme = useResolvedTheme();
  const topology = useAppStore((s) => s.topology);
  const expanded = useAppStore((s) => s.expanded);
  const containerStatus = useAppStore((s) => s.containerStatus);
  const selection = useAppStore((s) => s.selection);
  const { tool, snapToGrid, showMinimap, deployStatus } = useAppShallow((s) => ({
    tool: s.tool, snapToGrid: s.snapToGrid, showMinimap: s.showMinimap, deployStatus: s.deployStatus,
  }));

  // Captures/traffic in progress. /runtime returns a new array every poll, so
  // re-index only when what the canvas shows changes.
  const activityList = useAppStore((s) => s.activity);
  const activityKey = activityList.map((a) => `${a.kind}:${a.job_id}:${(a.node_ids ?? []).join(',')}:${(a.connection_ids ?? []).join(',')}`).join('|');
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const activity = useMemo(() => activityIndex(activityList), [activityKey]);

  // ── Projection → local React Flow state (local keeps in-flight drags) ──
  const projection = useMemo(
    () => project({ topology, scope, expanded, containerStatus, selection, activity }),
    [topology, scope, expanded, containerStatus, selection, activity],
  );
  const [nodes, setNodes] = useState<CanvasNode[]>(projection.nodes);
  const [edges, setEdges] = useState<CanvasEdge[]>(projection.edges);
  const [seen, setSeen] = useState(projection);
  if (seen !== projection) {
    setSeen(projection);
    setNodes((prev) => {
      const prevById = new Map(prev.map((n) => [n.id, n]));
      return projection.nodes.map((n) => {
        const p = prevById.get(n.id);
        if (!p) return n;
        return { ...n, position: p.dragging ? p.position : n.position, dragging: p.dragging, measured: p.measured } as CanvasNode;
      });
    });
    setEdges(projection.edges);
  }

  const onNodesChange = useCallback((changes: NodeChange<CanvasNode>[]) => {
    setNodes((nds) => applyNodeChanges(changes.filter((c) => c.type !== 'remove'), nds));
  }, []);
  const onEdgesChange = useCallback((changes: EdgeChange<CanvasEdge>[]) => {
    setEdges((eds) => applyEdgeChanges(changes.filter((c) => c.type !== 'remove'), eds));
  }, []);

  useOnSelectionChange({
    onChange: useCallback(({ nodes: n, edges: e }: { nodes: CanvasNode[]; edges: CanvasEdge[] }) => {
      useAppStore.getState().setSelection({ nodeIds: n.map((x) => x.id), edgeIds: e.map((x) => x.id) });
    }, []),
  });

  // ── Fit when the scope changes (after the new nodes are measured) ──
  const scopeKey = scopeKeyOf(scope);
  const nodesInitialized = useNodesInitialized();
  const [fitKey, setFitKey] = useState(0);
  const [lastScope, setLastScope] = useState(scopeKey);
  if (lastScope !== scopeKey) {
    setLastScope(scopeKey);
    setFitKey((k) => k + 1);
  }
  const fittedKey = useRef(-1);
  useEffect(() => {
    if (nodesInitialized && fittedKey.current !== fitKey) {
      fittedKey.current = fitKey;
      void rf.fitView({ padding: 0.2, maxZoom: 1.25, duration: 0 });
    }
  }, [fitKey, nodesInitialized, rf]);

  // ── Mutations ──
  const removeItems = useCallback((nodeIds: string[], edgeIds: string[]) => {
    if (readOnly) return;
    const count = nodeIds.length + edgeIds.length;
    if (!count) return;
    const st = useAppStore.getState();
    st.deleteItems(nodeIds, edgeIds);
    st.clearSelection();
    toast(`Deleted ${count} item${count === 1 ? '' : 's'}`, { action: { label: 'Undo', onClick: () => undo() } });
  }, [readOnly]);

  const drillInto = useCallback((id: string) => {
    const hit = locate(useAppStore.getState().topology, id);
    if (hit?.kind === 'site') onNavigate({ level: 'site', siteId: id });
    else if (hit?.kind === 'subnet') onNavigate({ level: 'subnet', siteId: hit.site.id, subnetId: id });
  }, [onNavigate]);

  /** Expand/collapse in place; when expanding, nudge siblings so the grown group does not cover them. */
  const toggleExpand = useCallback((id: string) => {
    const st = useAppStore.getState();
    const wasExpanded = !!st.expanded[id];
    st.toggleExpanded(id);
    if (wasExpanded || readOnly) return;
    const before = rf.getNodes().find((n) => n.id === id);
    const after = project({ topology: st.topology, scope, expanded: { ...st.expanded, [id]: true } }).nodes.find((n) => n.id === id);
    if (!before || !after) return;
    const oldW = before.width ?? 0, oldH = before.height ?? 0;
    const newW = after.width ?? 0, newH = after.height ?? 0;
    const dx = newW - oldW, dy = newH - oldH;
    if (dx <= 0 && dy <= 0) return;
    const gx = before.position.x, gy = before.position.y;
    const moves: { id: string; position: Position }[] = [];
    for (const n of rf.getNodes()) {
      if (n.id === id || n.parentId !== before.parentId) continue;
      const w = n.width ?? 0, h = n.height ?? 0;
      const overlapsX = n.position.x < gx + newW && n.position.x + w > gx;
      const overlapsY = n.position.y < gy + newH && n.position.y + h > gy;
      let nx = n.position.x, ny = n.position.y;
      if (dy > 0 && n.position.y >= gy + oldH - 1 && overlapsX) ny += dy;
      else if (dx > 0 && n.position.x >= gx + oldW - 1 && overlapsY) nx += dx;
      if (nx !== n.position.x || ny !== n.position.y) moves.push({ id: n.id, position: toStoredPosition({ position: { x: nx, y: ny }, parentId: n.parentId }, rf.getNodes()) });
    }
    if (moves.length) st.moveNodes(moves);
  }, [rf, scope, readOnly]);

  const actions = useMemo<CanvasActions>(() => ({
    drillInto,
    openTerminal: (c) => useAppStore.getState().openTerminal(c),
    toggleExpand,
    duplicate: (ids) => {
      if (readOnly) return;
      const st = useAppStore.getState();
      const created = st.duplicateNodes(ids);
      if (created.length) st.selectNodes(created);
    },
    remove: (ids) => removeItems(ids, []),
    inspect: (id) => {
      const st = useAppStore.getState();
      st.selectNodes([id]);
      st.setInspectorOpen(true);
    },
    canOpenTerminal: deployStatus === 'deployed',
    readOnly,
  }), [drillInto, removeItems, deployStatus, readOnly, toggleExpand]);

  /** Lay out the scope's top-level nodes using their rendered sizes (expanded groups included). */
  const autoLayout = useCallback((expandedOverride?: Record<string, true>) => {
    if (readOnly) return;
    const st = useAppStore.getState();
    const top = project({ topology: st.topology, scope, expanded: expandedOverride ?? st.expanded }).nodes.filter((n) => !n.parentId);
    const sizes = new Map(top.map((n) => [n.id, { width: n.width ?? 0, height: n.height ?? 0 }]));
    st.applyLayout(scope, st.layoutMode, sizes);
    window.setTimeout(() => void rf.fitView({ padding: 0.2, maxZoom: 1.25, duration: 200 }), 30);
  }, [scope, rf, readOnly]);

  // ── Adding entities (toolbar, context menu, drop) ──
  const { requestAdd, requestBulkDevices, requestBulkConnections } = useAddEntity();

  /** Resolve where an "add" lands: inside an expanded group under `at`, or at the scope's own level. */
  const resolveTarget = useCallback((at?: Position) => {
    let siteId = scope.level !== 'root' ? scope.siteId : undefined;
    let subnetId = scope.level === 'subnet' ? scope.subnetId : undefined;
    let stored = at;
    if (at) {
      const groups = rf.getNodes().filter((n): n is Extract<CanvasNode, { type: 'group' }> => n.type === 'group');
      // deepest first: subnet groups beat site groups
      const hits = groups
        .map((g) => ({ g, abs: rf.getInternalNode(g.id)?.internals.positionAbsolute }))
        .filter(({ g, abs }) => abs && at.x >= abs.x && at.y >= abs.y && at.x <= abs.x + g.data.width && at.y <= abs.y + g.data.height)
        .sort((a) => (a.g.data.entity === 'subnet' ? -1 : 1));
      const hit = hits[0];
      if (hit && hit.abs) {
        const data = hit.g.data as GroupNodeData;
        stored = { x: at.x - hit.abs.x + data.origin.x, y: at.y - hit.abs.y + data.origin.y };
        if (data.entity === 'subnet') { subnetId = hit.g.id; siteId = data.siteId; }
        else { siteId = hit.g.id; subnetId = undefined; }
      }
    }
    return { siteId, subnetId, at: stored };
  }, [scope, rf]);

  const centerOn = (at: Position | undefined, size: { width: number; height: number }): Position | undefined =>
    at ? { x: Math.round((at.x - size.width / 2) / GRID) * GRID, y: Math.round((at.y - size.height / 2) / GRID) * GRID } : undefined;

  const handleAdd = useCallback((item: PaletteItem, at?: Position, immediate = false) => {
    if (readOnly) return;
    const target = resolveTarget(at);
    const size = item.kind === 'site' ? NODE_SIZE.site : item.kind === 'subnet' ? NODE_SIZE.subnet : NODE_SIZE.device;
    // A click-to-add at the scope level: sites need no container; subnets/devices use the scope's own site/subnet.
    requestAdd(item, { siteId: item.kind === 'site' ? undefined : target.siteId, subnetId: item.kind === 'device' ? target.subnetId : undefined, at: centerOn(target.at, size) }, { immediate });
  }, [readOnly, resolveTarget, requestAdd]);

  // ── Hotkeys ──
  useCanvasHotkeys(useMemo(() => ({
    deleteSelection: () => { const s = useAppStore.getState().selection; removeItems(s.nodeIds, s.edgeIds); },
    duplicateSelection: () => actions.duplicate(useAppStore.getState().selection.nodeIds),
    selectAll: () => useAppStore.getState().selectNodes(rf.getNodes().map((n) => n.id)),
    clearSelection: () => useAppStore.getState().clearSelection(),
    undo: () => { if (!readOnly) undo(); },
    redo: () => { if (!readOnly) redo(); },
    save: onSave,
    autoLayout: () => autoLayout(),
    toggleExpandSelection: () => {
      const st = useAppStore.getState();
      const ok = new Set(expandableIds(st.topology, scope));
      for (const id of st.selection.nodeIds) if (ok.has(id)) toggleExpand(id);
    },
    openSelection: () => {
      const ids = useAppStore.getState().selection.nodeIds;
      if (ids.length === 1) drillInto(ids[0]);
    },
    commandPalette: () => useAppStore.getState().setCommandPaletteOpen(true),
    toggleSidebar: () => { const st = useAppStore.getState(); st.setSidebarOpen(!st.sidebarOpen); },
    toggleInspector: () => { const st = useAppStore.getState(); st.setInspectorOpen(!st.inspectorOpen); },
  }), [removeItems, actions, rf, readOnly, onSave, autoLayout, scope, drillInto, toggleExpand]));

  // ── React Flow event handlers ──
  const onConnect = useCallback((c: Connection) => {
    if (readOnly) return;
    const id = useAppStore.getState().addConnection({ from: c.source, to: c.target });
    if (!id) toast.error("These can't be linked directly", { description: 'Hosts link within their subnet; routers link subnets and sites.' });
  }, [readOnly]);

  const onNodeDragStop = useCallback<OnNodeDrag<CanvasNode>>((_e, _node, dragged) => {
    const all = rf.getNodes();
    useAppStore.getState().moveNodes(dragged.map((n) => ({ id: n.id, position: toStoredPosition(n, all) })));
  }, [rf]);

  const onNodeDoubleClick = useCallback<NodeMouseHandler<CanvasNode>>((_e, node) => {
    if (node.type === 'device') {
      if (deployStatus === 'deployed') useAppStore.getState().openTerminal(node.data.container);
      else actions.inspect(node.id);
    } else {
      drillInto(node.id);
    }
  }, [deployStatus, actions, drillInto]);

  const [ctxTarget, setCtxTarget] = useState<ContextTarget | null>(null);
  const onPaneContextMenu = useCallback((e: MouseEvent | React.MouseEvent) => {
    setCtxTarget({ kind: 'pane', flowPosition: rf.screenToFlowPosition({ x: e.clientX, y: e.clientY }) });
  }, [rf]);
  const onNodeContextMenu = useCallback<NodeMouseHandler<CanvasNode>>((_e, node) => {
    const sel = useAppStore.getState().selection.nodeIds;
    if (sel.length > 1 && sel.includes(node.id)) setCtxTarget({ kind: 'selection', nodeIds: sel });
    else setCtxTarget({ kind: 'node', node });
  }, []);
  const onEdgeContextMenu = useCallback<EdgeMouseHandler<CanvasEdge>>((_e, edge) => setCtxTarget({ kind: 'edge', id: edge.id }), []);
  const onSelectionContextMenu = useCallback((_e: React.MouseEvent, sel: CanvasNode[]) => setCtxTarget({ kind: 'selection', nodeIds: sel.map((n) => n.id) }), []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    if (readOnly) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, [readOnly]);
  const onDrop = useCallback((e: React.DragEvent) => {
    const item = readDragPayload(e);
    if (!item) return;
    e.preventDefault();
    handleAdd(item, rf.screenToFlowPosition({ x: e.clientX, y: e.clientY }), true);
  }, [handleAdd, rf]);

  const zoomFrame = useRef<number | null>(null);
  const onViewportChange = useCallback((vp: { zoom: number }) => {
    if (zoomFrame.current !== null) return;
    zoomFrame.current = requestAnimationFrame(() => {
      zoomFrame.current = null;
      useAppStore.getState().setZoom(vp.zoom);
    });
  }, []);

  // ── Derived bits for chrome ──
  const expandable = useMemo(() => expandableIds(topology, scope), [topology, scope]);
  const expandedCount = expandable.filter((id) => expanded[id]).length;
  const emptyLabel = scope.level === 'root' ? 'site' : scope.level === 'site' ? 'subnet' : 'device';

  return (
    <CanvasActionsContext.Provider value={actions}>
      <CanvasContextMenu
        scope={scope}
        target={ctxTarget}
        readOnly={readOnly}
        isExpanded={(id) => !!expanded[id]}
        canOpenTerminal={deployStatus === 'deployed'}
        canCapture={deployStatus === 'deployed'}
        captureOf={(kind, id) => (kind === 'edge' ? activity.captureConnections.get(id) : activity.captureNodes.get(id))}
        onCaptureLink={(connectionId) => useAppStore.getState().openCaptureDialog({ kind: 'link', connectionId })}
        onCaptureNode={(nodeId) => useAppStore.getState().openCaptureDialog({ kind: 'interface', nodeId })}
        onOpenCapture={(jobId) => openCaptureTab(jobId)}
        onStopCapture={(jobId) => void stopCapture(jobId)}
        onTraffic={(nodeId) => openTrafficPanel({ client: nodeId })}
        onAdd={(item, at) => handleAdd(item, at)}
        onDrill={drillInto}
        onToggleExpand={actions.toggleExpand}
        onTerminal={(id) => { const hit = locate(topology, id); if (hit?.kind === 'container') actions.openTerminal(hit.container); }}
        onDuplicate={actions.duplicate}
        onDelete={removeItems}
        onSelectAll={() => useAppStore.getState().selectNodes(rf.getNodes().map((n) => n.id))}
        onAutoLayout={() => autoLayout()}
        onBulkDevices={scope.level === 'subnet' ? () => requestBulkDevices(scope.subnetId) : undefined}
        onBulkConnections={() => requestBulkConnections(scope)}
      >
        <div className="relative h-full w-full" data-testid="topology-canvas">
          <ReactFlow<CanvasNode, CanvasEdge>
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            colorMode={theme}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStop={onNodeDragStop}
            onNodeDoubleClick={onNodeDoubleClick}
            onPaneContextMenu={onPaneContextMenu}
            onNodeContextMenu={onNodeContextMenu}
            onEdgeContextMenu={onEdgeContextMenu}
            onSelectionContextMenu={onSelectionContextMenu}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onViewportChange={onViewportChange}
            connectionMode={ConnectionMode.Loose}
            connectionLineComponent={ConnectionLine}
            connectionRadius={28}
            isValidConnection={(c) => c.source !== c.target}
            nodesDraggable={!readOnly}
            nodesConnectable={!readOnly}
            selectionOnDrag={tool === 'select'}
            selectionMode={SelectionMode.Partial}
            panOnDrag={tool === 'select' ? [1] : true}
            panOnScroll
            zoomOnDoubleClick={false}
            snapToGrid={snapToGrid}
            snapGrid={[GRID, GRID]}
            deleteKeyCode={null}
            multiSelectionKeyCode={['Meta', 'Control', 'Shift']}
            minZoom={0.15}
            maxZoom={2.5}
            proOptions={{ hideAttribution: true }}
            className={tool === 'pan' ? 'cursor-grab' : undefined}
          >
            <Background variant={BackgroundVariant.Dots} gap={GRID * 2} size={1.2} />
            <Controls position="bottom-left" showInteractive={false} className="!m-3" />
            {showMinimap ? (
              <MiniMap
                position="bottom-right"
                className="!m-3"
                pannable
                zoomable
                nodeStrokeWidth={0}
                nodeBorderRadius={4}
                nodeColor={(n) => (n.type === 'device' ? colorFor((n as CanvasNode & { type: 'device' }).data.container.type) : n.type === 'site' ? 'var(--accent)' : n.type === 'group' ? 'transparent' : 'var(--info)')}
              />
            ) : null}
            <CanvasToolbar
              scope={scope}
              readOnly={readOnly}
              onAdd={(item) => handleAdd(item)}
              onBulkDevices={scope.level === 'subnet' ? () => requestBulkDevices(scope.subnetId) : undefined}
              onBulkConnections={() => requestBulkConnections(scope)}
              onAutoLayout={() => autoLayout()}
              expandableCount={expandable.length}
              expandedCount={expandedCount}
              onExpandAll={() => {
                const st = useAppStore.getState();
                st.setExpanded(expandable, true);
                const next: Record<string, true> = { ...st.expanded };
                for (const id of expandable) next[id] = true;
                autoLayout(next);
              }}
              onCollapseAll={() => useAppStore.getState().setExpanded(expandable, false)}
            />
          </ReactFlow>

          {projection.nodes.length === 0 ? (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <EmptyState
                className="pointer-events-auto rounded-xl border border-dashed border-border-strong bg-surface/80 backdrop-blur-sm"
                title={`No ${emptyLabel}s yet`}
                description={
                  scope.level === 'root'
                    ? 'Sites group subnets by location. Add one to begin, or drag from the palette.'
                    : scope.level === 'site'
                      ? 'Each subnet gets a gateway router and a switch automatically.'
                      : 'Add devices here and link them to the switch.'
                }
                action={
                  !readOnly ? (
                    <Button variant="primary" size="sm" onClick={() => handleAdd({ kind: scope.level === 'root' ? 'site' : scope.level === 'site' ? 'subnet' : 'device', ...(scope.level === 'subnet' ? { type: 'workstation' } : {}) } as PaletteItem)}>
                      <Plus /> Add {emptyLabel}
                    </Button>
                  ) : undefined
                }
              />
            </div>
          ) : null}
        </div>
      </CanvasContextMenu>

    </CanvasActionsContext.Provider>
  );
}
