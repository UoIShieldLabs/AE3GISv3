import { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  useReactFlow,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { DeviceNode } from './nodes/DeviceNode';
import { NeonEdge, NeonEdgeDirect } from './edges/NeonEdge';
import { ContextMenu, type ContextMenuItem } from './ui/ContextMenu';
import { Toolbar } from './Toolbar';
import { ContainerDialog } from './dialogs/ContainerDialog';
import { BulkContainerDialog } from './dialogs/BulkContainerDialog';
import { ConnectionDialog } from './dialogs/ConnectionDialog';
import { BulkConnectionDialog } from './dialogs/BulkConnectionDialog';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
import { TopologyDispatchContext } from '../store/TopologyContext';
import { computeLayout, computeCircleLayout, computeGridLayout, type LayoutMode } from '../utils/autoLayout';
import { generateId } from '../utils/idGenerator';
import type { Subnet, Container, ContainerType } from '../data/sampleTopology';

const nodeTypes = { device: DeviceNode };
const edgeTypes = { neon: NeonEdge, neonDirect: NeonEdgeDirect };

// Layout hierarchy: lower number = higher rank (router → switch → everything else)
const TYPE_RANK: Partial<Record<string, number>> = { router: 0, switch: 1 };
const getTypeRank = (type: string) => TYPE_RANK[type] ?? 2;

const typeColors: Record<ContainerType, string> = {
  'router': '#ff00ff',
  'firewall': '#ff3344',
  'switch': '#ffaa00',
  'web-server': '#00ff9f',
  'file-server': '#00d4ff',
  'plc': '#ffaa00',
  'workstation': '#4466ff',
};

interface LanViewProps {
  subnet: Subnet;
  siteId: string;
  onSelectContainer: (container: Container) => void;
  onOpenTerminal: (container: Container) => void;
  onDeselect: () => void;
  readOnly?: boolean;
}

export function LanView({ subnet, siteId, onSelectContainer, onOpenTerminal, onDeselect, readOnly }: LanViewProps) {
  const dispatch = useContext(TopologyDispatchContext);
  const { fitView } = useReactFlow();

  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; items: ContextMenuItem[] } | null>(null);
  const [containerDialog, setContainerDialog] = useState<{ open: boolean; initial?: Container }>({ open: false });
  const [bulkDialog, setBulkDialog] = useState(false);
  const [connDialog, setConnDialog] = useState(false);
  const [bulkConnDialog, setBulkConnDialog] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ containerId: string; name: string } | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  // const [posOverrides, setPosOverrides] = useState<Map<string, { x: number; y: number }>>(new Map());
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('dagre');

  const handleSelect = useCallback(
    (container: Container) => onSelectContainer(container),
    [onSelectContainer]
  );

  const handleOpenTerminal = useCallback(
    (container: Container) => onOpenTerminal(container),
    [onOpenTerminal]
  );

  const visibleContainers = useMemo(
    () => [...subnet.containers.filter(c => c.type !== 'firewall')]
      .sort((a, b) => getTypeRank(a.type) - getTypeRank(b.type)),
    [subnet.containers]
  );
  const visibleContainerIds = useMemo(
    () => new Set(visibleContainers.map(c => c.id)),
    [visibleContainers]
  );
  const visibleConnections = useMemo(
    () => subnet.connections.filter(
      conn => visibleContainerIds.has(conn.from) && visibleContainerIds.has(conn.to)
    ),
    [subnet.connections, visibleContainerIds]
  );
  // Edges oriented to flow router→switch→devices for hierarchy-aware layouts
  const hierarchyEdges = useMemo(() => {
    const idToRank = new Map(subnet.containers.map(c => [c.id, getTypeRank(c.type)]));
    return visibleConnections.map(c => {
      const fromRank = idToRank.get(c.from) ?? 2;
      const toRank = idToRank.get(c.to) ?? 2;
      return fromRank <= toRank
        ? { source: c.from, target: c.to }
        : { source: c.to, target: c.from };
    });
  }, [visibleConnections, subnet.containers]);

  // Sync nodes with subnet data and layout
  const prevLayoutMode = useRef(layoutMode);

  useEffect(() => {
    const layoutChanged = layoutMode !== prevLayoutMode.current;
    prevLayoutMode.current = layoutMode;

    const layoutNodes = visibleContainers.map(c => ({ id: c.id, width: 110, height: 100 }));
    let computedPositions: Map<string, { x: number; y: number }> = new Map();

    if (layoutNodes.length > 0) {
      const nodePriority = new Map(visibleContainers.map(c => [c.id, getTypeRank(c.type)]));
      if (layoutMode === 'circle') {
        computedPositions = computeCircleLayout(
          layoutNodes,
          hierarchyEdges,
          { nodePriority },
        );
      } else if (layoutMode === 'grid') {
        computedPositions = computeGridLayout(layoutNodes);
      } else {
        computedPositions = computeLayout(
          layoutNodes,
          hierarchyEdges,
          { direction: 'TB', nodeSpacing: 80, rankSpacing: 100 }
        );
      }
    }

    setNodes((currentNodes) => {
      return visibleContainers.map((container) => {
        // If layout didn't change, try to preserve existing position
        if (!layoutChanged) {
          const existingNode = currentNodes.find(n => n.id === container.id);
          if (existingNode) {
            return {
              ...existingNode,
              data: { ...existingNode.data, container, onSelect: handleSelect, onOpenTerminal: handleOpenTerminal },
            };
          }
        }

        // Otherwise use computed layout position
        const pos = computedPositions.get(container.id) || { x: 0, y: 0 };
        return {
          id: container.id,
          type: 'device',
          position: pos,
          data: {
            container,
            onSelect: handleSelect,
            onOpenTerminal: handleOpenTerminal,
          },
        };
      });
    });
  }, [visibleContainers, visibleConnections, layoutMode, handleSelect, setNodes]);

  // Sync edges
  useEffect(() => {
    setEdges(
      hierarchyEdges.map((edge, i) => {
        const sourceContainer = visibleContainers.find(c => c.id === edge.source);
        const color = sourceContainer ? typeColors[sourceContainer.type] : '#00ff9f';
        return {
          id: `lan-edge-${i}`,
          source: edge.source,
          target: edge.target,
          type: layoutMode === 'circle' ? 'neonDirect' : 'neon',
          data: { color },
        };
      })
    );
  }, [hierarchyEdges, visibleContainers, layoutMode, setEdges]);



  // Context menu handlers
  const onPaneContextMenu = useCallback((event: MouseEvent | React.MouseEvent) => {
    event.preventDefault();
    setCtxMenu({
      x: event.clientX,
      y: event.clientY,
      items: [
        { label: 'Add Container', onClick: () => setContainerDialog({ open: true }) },
        { label: 'Bulk Add Containers', onClick: () => setBulkDialog(true) },
        { label: 'Add Connection', onClick: () => setConnDialog(true) },
        { label: 'Bulk Add Connections', onClick: () => setBulkConnDialog(true) },
      ],
    });
  }, []);

  const onNodeContextMenu = useCallback((event: React.MouseEvent, node: Node) => {
    event.preventDefault();
    const container = visibleContainers.find(c => c.id === node.id);
    if (!container) return;
    setCtxMenu({
      x: event.clientX,
      y: event.clientY,
      items: [
        { label: 'Edit Container', onClick: () => setContainerDialog({ open: true, initial: container }) },
        { label: 'Delete Container', onClick: () => setDeleteConfirm({ containerId: container.id, name: container.name }), danger: true },
      ],
    });
  }, [visibleContainers]);

  const onEdgeContextMenu = useCallback((event: React.MouseEvent, edge: Edge) => {
    event.preventDefault();
    const idx = Number(edge.id.replace('lan-edge-', ''));
    const conn = visibleConnections[idx];
    if (!conn) return;
    setCtxMenu({
      x: event.clientX,
      y: event.clientY,
      items: [
        {
          label: 'Delete Connection',
          danger: true,
          onClick: () => dispatch({
            type: 'DELETE_SUBNET_CONNECTION',
            payload: { siteId, subnetId: subnet.id, from: conn.from, to: conn.to },
          }),
        },
      ],
    });
  }, [visibleConnections, subnet.id, siteId, dispatch]);

  // CRUD handlers
  const handleAddContainer = useCallback((data: {
    name: string; type: ContainerType; ip: string; image: string;
    status: 'running' | 'stopped' | 'paused'; metadata: Record<string, string>;
    persistencePaths: string[];
  }) => {
    dispatch({
      type: 'ADD_CONTAINER',
      payload: {
        siteId,
        subnetId: subnet.id,
        container: {
          id: generateId(),
          name: data.name,
          type: data.type,
          ip: data.ip,
          image: data.image || undefined,
          status: data.status,
          metadata: Object.keys(data.metadata).length > 0 ? data.metadata : undefined,
          persistencePaths: data.persistencePaths.length > 0 ? data.persistencePaths : undefined,
        },
      },
    });
  }, [dispatch, siteId, subnet.id]);

  const handleBulkAdd = useCallback((entries: { name: string; type: ContainerType; ip: string }[]) => {
    for (const entry of entries) {
      dispatch({
        type: 'ADD_CONTAINER',
        payload: {
          siteId,
          subnetId: subnet.id,
          container: {
            id: generateId(),
            name: entry.name,
            type: entry.type,
            ip: entry.ip,
            status: 'running',
          },
        },
      });
    }
  }, [dispatch, siteId, subnet.id]);

  const handleEditContainer = useCallback((data: {
    name: string; type: ContainerType; ip: string; image: string;
    status: 'running' | 'stopped' | 'paused'; metadata: Record<string, string>;
    persistencePaths: string[];
  }) => {
    if (!containerDialog.initial) return;
    dispatch({
      type: 'UPDATE_CONTAINER',
      payload: {
        siteId,
        subnetId: subnet.id,
        containerId: containerDialog.initial.id,
        updates: {
          name: data.name,
          type: data.type,
          ip: data.ip,
          image: data.image || undefined,
          status: data.status,
          metadata: Object.keys(data.metadata).length > 0 ? data.metadata : undefined,
          persistencePaths: data.persistencePaths.length > 0 ? data.persistencePaths : undefined,
        },
      },
    });
  }, [dispatch, siteId, subnet.id, containerDialog.initial]);

  const handleDeleteContainer = useCallback(() => {
    if (!deleteConfirm) return;
    dispatch({
      type: 'DELETE_CONTAINER',
      payload: { siteId, subnetId: subnet.id, containerId: deleteConfirm.containerId },
    });
    setDeleteConfirm(null);
  }, [dispatch, siteId, subnet.id, deleteConfirm]);

  const handleAddConnection = useCallback((data: { from: string; to: string; label: string }) => {
    dispatch({
      type: 'ADD_SUBNET_CONNECTION',
      payload: {
        siteId,
        subnetId: subnet.id,
        connection: { from: data.from, to: data.to, label: data.label || undefined },
      },
    });
  }, [dispatch, siteId, subnet.id]);

  const handleBulkConnections = useCallback((connections: { from: string; to: string }[]) => {
    for (const conn of connections) {
      dispatch({
        type: 'ADD_SUBNET_CONNECTION',
        payload: {
          siteId,
          subnetId: subnet.id,
          connection: { from: conn.from, to: conn.to },
        },
      });
    }
  }, [dispatch, siteId, subnet.id]);

  // Interactive edge connection
  const onConnect = useCallback((params: Connection) => {
    if (params.source && params.target) {
      dispatch({
        type: 'ADD_SUBNET_CONNECTION',
        payload: {
          siteId,
          subnetId: subnet.id,
          connection: { from: params.source, to: params.target },
        },
      });
    }
  }, [dispatch, siteId, subnet.id]);

  // Persist drag positions - local state only via useNodesState
  const onNodeDragStop = useCallback(() => {
    // Optionally we could save this to a ref if we wanted to persist across re-layouts manually,
    // but standard behavior is fine.
  }, []);

  const handleAutoLayout = useCallback(() => {
    // Force re-layout logic
    // We can trigger this by momentarily toggling layoutMode or just recalling the computation.
    // Since our useEffect depends on layoutMode, we can just use that.
    // Or we can explicitly setNodes with new layout.
    // For now, let's assuming switching layout mode is the trigger.
    // If we want a 'Refresh Layout' button, we'd need a trigger.
    // The current Toolbar passes onAutoLayout.
    // Let's implement it to reset positions to the current layoutMode's computed positions.

    const layoutNodes = visibleContainers.map(c => ({ id: c.id, width: 110, height: 100 }));
    const nodePriority = new Map(visibleContainers.map(c => [c.id, getTypeRank(c.type)]));
    let computedPositions: Map<string, { x: number; y: number }> = new Map();
    if (layoutMode === 'circle') {
      computedPositions = computeCircleLayout(
        layoutNodes,
        hierarchyEdges,
        { nodePriority },
      );
    } else if (layoutMode === 'grid') {
      computedPositions = computeGridLayout(layoutNodes);
    } else {
      computedPositions = computeLayout(
        layoutNodes,
        hierarchyEdges,
        { direction: 'TB', nodeSpacing: 80, rankSpacing: 100 }
      );
    }

    setNodes((nds) => nds.map(n => ({
      ...n,
      position: computedPositions.get(n.id) || { x: 0, y: 0 }
    })));

    setTimeout(() => fitView({ padding: 0.3 }), 50);
  }, [fitView, visibleContainers, hierarchyEdges, layoutMode, setNodes]);

  const takenIps = useMemo(
    () => subnet.containers.map(c => c.ip),
    [subnet.containers]
  );

  const connectionNodes = useMemo(
    () => visibleContainers.map(c => ({ id: c.id, name: c.name })),
    [visibleContainers]
  );

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        maxZoom={3}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onPaneContextMenu={readOnly ? undefined : onPaneContextMenu}
        onNodeContextMenu={readOnly ? undefined : onNodeContextMenu}
        onEdgeContextMenu={readOnly ? undefined : onEdgeContextMenu}
        onConnect={readOnly ? undefined : onConnect}
        onNodeDragStop={readOnly ? undefined : onNodeDragStop}
        onPaneClick={onDeselect}
        connectionLineStyle={{ stroke: '#00d4ff', strokeWidth: 1.5, opacity: 0.6 }}
      >
        <Background
          color="rgba(0, 255, 159, 0.03)"
          gap={30}
          size={1}
        />
        <Controls showInteractive={false} />
      </ReactFlow>

      <Toolbar
        onAdd={() => setContainerDialog({ open: true })}
        addLabel="Container"
        onAutoLayout={handleAutoLayout}
        onBulkAdd={() => setBulkDialog(true)}
        layoutMode={layoutMode}
        onLayoutModeChange={setLayoutMode}
        readOnly={readOnly}
      />

      <div className="scale-label">
        LAN Detail — {subnet.name} ({subnet.cidr})
      </div>

      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          items={ctxMenu.items}
          onClose={() => setCtxMenu(null)}
        />
      )}

      {!readOnly && (
        <>
          <ContainerDialog
            open={containerDialog.open}
            onClose={() => setContainerDialog({ open: false })}
            onSubmit={containerDialog.initial ? handleEditContainer : handleAddContainer}
            initial={containerDialog.initial}
            subnetCidr={subnet.cidr}
            takenIps={takenIps}
          />

          <BulkContainerDialog
            open={bulkDialog}
            onClose={() => setBulkDialog(false)}
            onSubmit={handleBulkAdd}
            subnetCidr={subnet.cidr}
            takenIps={takenIps}
          />

          <ConnectionDialog
            open={connDialog}
            onClose={() => setConnDialog(false)}
            onSubmit={handleAddConnection}
            availableNodes={connectionNodes}
          />

          <BulkConnectionDialog
            open={bulkConnDialog}
            onClose={() => setBulkConnDialog(false)}
            onSubmit={handleBulkConnections}
            availableNodes={connectionNodes}
            existingConnections={subnet.connections}
          />

          <ConfirmDialog
            open={!!deleteConfirm}
            title="Delete Container"
            message={`Delete "${deleteConfirm?.name}"? All connections to this container will be removed.`}
            onConfirm={handleDeleteContainer}
            onCancel={() => setDeleteConfirm(null)}
          />
        </>
      )}
    </div>
  );
}
