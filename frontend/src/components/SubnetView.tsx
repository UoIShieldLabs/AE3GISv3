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
import { SubnetCloudNode } from './nodes/SubnetCloudNode';
import { RouterNode } from './nodes/RouterNode';
import { NeonEdge, NeonEdgeDirect } from './edges/NeonEdge';
import { ContextMenu, type ContextMenuItem } from './ui/ContextMenu';
import { Toolbar } from './Toolbar';
import { SubnetDialog } from './dialogs/SubnetDialog';
import { ConnectionDialog } from './dialogs/ConnectionDialog';
import { BulkConnectionDialog } from './dialogs/BulkConnectionDialog';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
import { TopologyDispatchContext } from '../store/TopologyContext';
import { computeLayout, computeCircleLayout, computeGridLayout, type LayoutMode } from '../utils/autoLayout';
import { generateId } from '../utils/idGenerator';
import type { Site, Subnet, Container } from '../data/sampleTopology';

const nodeTypes = { subnetCloud: SubnetCloudNode, routerNode: RouterNode };
const edgeTypes = { neon: NeonEdge, neonDirect: NeonEdgeDirect };
const ROUTER_OFFSET = { x: 55, y: 150 }; // place router centered below subnet cloud

interface SubnetViewProps {
  site: Site;
  onSelectSubnet: (subnetId: string) => void;
  onOpenRouterTerminal: (container: Container) => void;
  readOnly?: boolean;
}

export function SubnetView({ site, onSelectSubnet, onOpenRouterTerminal, readOnly }: SubnetViewProps) {
  const dispatch = useContext(TopologyDispatchContext);
  const { fitView } = useReactFlow();

  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; items: ContextMenuItem[] } | null>(null);
  const [subnetDialog, setSubnetDialog] = useState<{ open: boolean; initial?: Subnet }>({ open: false });
  const [connDialog, setConnDialog] = useState(false);
  const [bulkConnDialog, setBulkConnDialog] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ subnetId: string; name: string } | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  // const [posOverrides, setPosOverrides] = useState<Map<string, { x: number; y: number }>>(new Map());
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('dagre');

  const handleDrillDown = useCallback(
    (subnetId: string) => onSelectSubnet(subnetId),
    [onSelectSubnet]
  );

  // Sync nodes with site data and layout
  const prevLayoutMode = useRef(layoutMode);

  useEffect(() => {
    const layoutChanged = layoutMode !== prevLayoutMode.current;
    prevLayoutMode.current = layoutMode;

    // Only subnet clouds participate in the auto-layout algorithm
    const layoutNodes = site.subnets.map(s => ({ id: s.id, width: 200, height: 120 }));
    let computedPositions: Map<string, { x: number; y: number }> = new Map();

    if (layoutNodes.length > 0) {
      if (layoutNodes.length === 1) {
        computedPositions.set(layoutNodes[0].id, { x: 400, y: 300 });
      } else if (layoutMode === 'circle') {
        computedPositions = computeCircleLayout(
          layoutNodes,
          site.subnetConnections.map(c => ({ source: c.from, target: c.to })),
        );
      } else if (layoutMode === 'grid') {
        computedPositions = computeGridLayout(layoutNodes);
      } else {
        computedPositions = computeLayout(
          layoutNodes,
          site.subnetConnections.map(c => ({ source: c.from, target: c.to })),
          { direction: 'TB', nodeSpacing: 100, rankSpacing: 120 }
        );
      }
    }

    setNodes((currentNodes) => {
      const newNodes: Node[] = [];

      for (const subnet of site.subnets) {
        // Subnet cloud node
        let cloudPos: { x: number; y: number };
        if (!layoutChanged) {
          const existing = currentNodes.find(n => n.id === subnet.id);
          cloudPos = existing?.position ?? computedPositions.get(subnet.id) ?? { x: 400, y: 300 };
        } else {
          cloudPos = computedPositions.get(subnet.id) ?? { x: 400, y: 300 };
        }

        // Container count excludes the auto-infra (router/switch) so the badge
        // only reflects user-added devices.
        const userContainerCount = subnet.containers.filter(
          c => c.type !== 'router' && c.type !== 'firewall' && c.type !== 'switch'
        ).length;

        newNodes.push({
          id: subnet.id,
          type: 'subnetCloud',
          position: cloudPos,
          data: {
            label: subnet.name,
            cidr: subnet.cidr,
            containerCount: userContainerCount,
            onDrillDown: handleDrillDown,
          },
        });

        // Gateway router node — positioned below the subnet cloud
        const gateway = subnet.containers.find(
          c => c.type === 'router' || c.type === 'firewall'
        );
        if (gateway) {
          const routerDefaultPos = {
            x: cloudPos.x + ROUTER_OFFSET.x,
            y: cloudPos.y + ROUTER_OFFSET.y,
          };
          let routerPos = routerDefaultPos;
          if (!layoutChanged) {
            const existingRouter = currentNodes.find(n => n.id === gateway.id);
            if (existingRouter) routerPos = existingRouter.position;
          }
          newNodes.push({
            id: gateway.id,
            type: 'routerNode',
            position: routerPos,
            draggable: true,
            connectable: false,
            data: { label: gateway.name, ip: gateway.ip, type: gateway.type },
          });
        }
      }

      return newNodes;
    });
  }, [site.subnets, site.subnetConnections, layoutMode, handleDrillDown, setNodes]);

  // Sync edges: internal subnet→router edges (dashed) + WAN router→router edges
  useEffect(() => {
    const newEdges: Edge[] = [];
    const edgeType = layoutMode === 'circle' ? 'neonDirect' : 'neon';

    // Internal edge: subnet cloud → its gateway router
    for (const subnet of site.subnets) {
      const gateway = subnet.containers.find(
        c => c.type === 'router' || c.type === 'firewall'
      );
      if (gateway) {
        newEdges.push({
          id: `internal-${subnet.id}`,
          source: subnet.id,
          target: gateway.id,
          type: 'neonDirect',
          data: { color: 'rgba(0,212,255,0.25)' },
          style: { strokeDasharray: '5 4' },
          animated: false,
        });
      }
    }

    // WAN edges: router-to-router (use fromContainer/toContainer when set)
    site.subnetConnections.forEach((conn, i) => {
      const source = conn.fromContainer ?? conn.from;
      const target = conn.toContainer ?? conn.to;
      newEdges.push({
        id: `wan-edge-${i}`,
        source,
        target,
        type: edgeType,
        data: { color: '#00d4ff', label: conn.label },
      });
    });

    setEdges(newEdges);
  }, [site.subnets, site.subnetConnections, layoutMode, setEdges]);



  // Context menu handlers
  const onPaneContextMenu = useCallback((event: MouseEvent | React.MouseEvent) => {
    event.preventDefault();
    setCtxMenu({
      x: event.clientX,
      y: event.clientY,
      items: [
        { label: 'Add Subnet', onClick: () => setSubnetDialog({ open: true }) },
        { label: 'Add Connection', onClick: () => setConnDialog(true) },
        { label: 'Bulk Add Connections', onClick: () => setBulkConnDialog(true) },
      ],
    });
  }, []);

  const onNodeContextMenu = useCallback((event: React.MouseEvent, node: Node) => {
    event.preventDefault();
    const subnet = site.subnets.find(s => s.id === node.id);
    if (!subnet) return;
    setCtxMenu({
      x: event.clientX,
      y: event.clientY,
      items: [
        { label: 'Edit Subnet', onClick: () => setSubnetDialog({ open: true, initial: subnet }) },
        { label: 'Delete Subnet', onClick: () => setDeleteConfirm({ subnetId: subnet.id, name: subnet.name }), danger: true },
      ],
    });
  }, [site.subnets]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    for (const subnet of site.subnets) {
      const gateway = subnet.containers.find(
        c => c.type === 'router' || c.type === 'firewall'
      );
      if (gateway?.id === node.id) {
        onOpenRouterTerminal(gateway);
        return;
      }
    }
  }, [site.subnets, onOpenRouterTerminal]);

  const onEdgeContextMenu = useCallback((event: React.MouseEvent, edge: Edge) => {
    event.preventDefault();
    const idx = Number(edge.id.replace('subnet-edge-', ''));
    const conn = site.subnetConnections[idx];
    if (!conn) return;
    setCtxMenu({
      x: event.clientX,
      y: event.clientY,
      items: [
        {
          label: 'Delete Connection',
          danger: true,
          onClick: () => dispatch({
            type: 'DELETE_INTER_SUBNET_CONNECTION',
            payload: { siteId: site.id, from: conn.from, to: conn.to },
          }),
        },
      ],
    });
  }, [site.subnetConnections, site.id, dispatch]);

  // CRUD handlers
  const handleAddSubnet = useCallback((data: { name: string; cidr: string }) => {
    dispatch({
      type: 'ADD_SUBNET',
      payload: {
        siteId: site.id,
        subnet: {
          id: generateId(),
          name: data.name,
          cidr: data.cidr,
          containers: [],
          connections: [],
        },
      },
    });
  }, [dispatch, site.id]);

  const handleEditSubnet = useCallback((data: { name: string; cidr: string }) => {
    if (!subnetDialog.initial) return;
    dispatch({
      type: 'UPDATE_SUBNET',
      payload: {
        siteId: site.id,
        subnetId: subnetDialog.initial.id,
        updates: { name: data.name, cidr: data.cidr },
      },
    });
  }, [dispatch, site.id, subnetDialog.initial]);

  const handleDeleteSubnet = useCallback(() => {
    if (!deleteConfirm) return;
    dispatch({ type: 'DELETE_SUBNET', payload: { siteId: site.id, subnetId: deleteConfirm.subnetId } });
    setDeleteConfirm(null);
  }, [dispatch, site.id, deleteConfirm]);

  const handleAddConnection = useCallback((data: { from: string; to: string; label: string }) => {
    dispatch({
      type: 'ADD_INTER_SUBNET_CONNECTION',
      payload: {
        siteId: site.id,
        connection: { from: data.from, to: data.to, label: data.label || undefined },
      },
    });
  }, [dispatch, site.id]);

  const handleBulkConnections = useCallback((connections: { from: string; to: string }[]) => {
    for (const conn of connections) {
      dispatch({
        type: 'ADD_INTER_SUBNET_CONNECTION',
        payload: {
          siteId: site.id,
          connection: { from: conn.from, to: conn.to },
        },
      });
    }
  }, [dispatch, site.id]);

  // Interactive edge connection
  const onConnect = useCallback((params: Connection) => {
    if (params.source && params.target) {
      dispatch({
        type: 'ADD_INTER_SUBNET_CONNECTION',
        payload: {
          siteId: site.id,
          connection: { from: params.source, to: params.target },
        },
      });
    }
  }, [dispatch, site.id]);

  // Persist drag positions - local state only via useNodesState
  const onNodeDrag = useCallback((_: React.MouseEvent, node: Node) => {
    const subnetByRouter = new Map<string, string>();
    const routerBySubnet = new Map<string, string>();

    for (const subnet of site.subnets) {
      const gateway = subnet.containers.find(
        c => c.type === 'router' || c.type === 'firewall'
      );
      if (gateway) {
        subnetByRouter.set(gateway.id, subnet.id);
        routerBySubnet.set(subnet.id, gateway.id);
      }
    }

    // Dragging subnet cloud moves its router with a fixed offset.
    if (routerBySubnet.has(node.id)) {
      const routerId = routerBySubnet.get(node.id)!;
      setNodes((nds) => nds.map((n) => {
        if (n.id === routerId) {
          return {
            ...n,
            position: {
              x: node.position.x + ROUTER_OFFSET.x,
              y: node.position.y + ROUTER_OFFSET.y,
            },
          };
        }
        return n;
      }));
      return;
    }

    // Dragging router moves its subnet cloud with the inverse offset.
    if (subnetByRouter.has(node.id)) {
      const subnetId = subnetByRouter.get(node.id)!;
      setNodes((nds) => nds.map((n) => {
        if (n.id === subnetId) {
          return {
            ...n,
            position: {
              x: node.position.x - ROUTER_OFFSET.x,
              y: node.position.y - ROUTER_OFFSET.y,
            },
          };
        }
        return n;
      }));
    }
  }, [site.subnets, setNodes]);

  const onNodeDragStop = useCallback((_: React.MouseEvent, _node: Node) => {
    // setPosOverrides(prev => new Map(prev).set(node.id, node.position));
  }, []);

  const handleAutoLayout = useCallback(() => {
    // Force re-layout logic by tricking the effect or explicit setNodes
    // Re-using the logic from LanView - if layoutMode didn't change, we might need a force flag?
    // Or just toggle layoutMode. 
    // Actually, the simplest for now is to let the user switch layout modes.
    // But if they click the button, they expect reset.
    // The previous implementation cleared posOverrides.
    // Here we can re-run the layout computation.

    // We can manually setNodes to computed positions.
    const layoutNodes = site.subnets.map(s => ({ id: s.id, width: 200, height: 120 }));
    let computedPositions: Map<string, { x: number; y: number }> = new Map();

    if (layoutNodes.length > 0) {
      if (layoutNodes.length === 1) {
        computedPositions.set(layoutNodes[0].id, { x: 400, y: 300 });
      } else if (layoutMode === 'circle') {
        computedPositions = computeCircleLayout(
          layoutNodes,
          site.subnetConnections.map(c => ({ source: c.from, target: c.to })),
        );
      } else if (layoutMode === 'grid') {
        computedPositions = computeGridLayout(layoutNodes);
      } else {
        computedPositions = computeLayout(
          layoutNodes,
          site.subnetConnections.map(c => ({ source: c.from, target: c.to })),
          { direction: 'TB', nodeSpacing: 100, rankSpacing: 120 }
        );
      }
    }

    const routerBySubnet = new Map<string, string>();
    for (const subnet of site.subnets) {
      const gateway = subnet.containers.find(
        c => c.type === 'router' || c.type === 'firewall'
      );
      if (gateway) routerBySubnet.set(subnet.id, gateway.id);
    }

    setNodes((nds) => nds.map((n) => {
      const cloudPos = computedPositions.get(n.id);
      if (cloudPos) {
        return { ...n, position: cloudPos };
      }

      for (const [subnetId, routerId] of routerBySubnet.entries()) {
        if (n.id === routerId) {
          const base = computedPositions.get(subnetId) || { x: 400, y: 300 };
          return {
            ...n,
            position: {
              x: base.x + ROUTER_OFFSET.x,
              y: base.y + ROUTER_OFFSET.y,
            },
          };
        }
      }

      return n;
    }));

    setTimeout(() => fitView({ padding: 0.4 }), 50);
  }, [fitView, site.subnets, site.subnetConnections, layoutMode, setNodes]);

  const connectionNodes = useMemo(
    () => site.subnets.map(s => ({ id: s.id, name: s.name })),
    [site.subnets]
  );

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.4 }}
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onPaneContextMenu={readOnly ? undefined : onPaneContextMenu}
        onNodeContextMenu={readOnly ? undefined : onNodeContextMenu}
        onNodeClick={onNodeClick}
        onNodeDrag={readOnly ? undefined : onNodeDrag}
        onEdgeContextMenu={readOnly ? undefined : onEdgeContextMenu}
        onConnect={readOnly ? undefined : onConnect}
        onNodeDragStop={readOnly ? undefined : onNodeDragStop}
        connectionLineStyle={{ stroke: '#00d4ff', strokeWidth: 1.5, opacity: 0.6 }}
      >
        <Background
          color="rgba(0, 212, 255, 0.04)"
          gap={40}
          size={1}
        />
        <Controls showInteractive={false} />
      </ReactFlow>

      <Toolbar
        onAdd={() => setSubnetDialog({ open: true })}
        addLabel="Subnet"
        onAutoLayout={handleAutoLayout}
        layoutMode={layoutMode}
        onLayoutModeChange={setLayoutMode}
        readOnly={readOnly}
      />

      <div className="scale-label">Subnet Overview — {site.name}</div>

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
          <SubnetDialog
            open={subnetDialog.open}
            onClose={() => setSubnetDialog({ open: false })}
            onSubmit={subnetDialog.initial ? handleEditSubnet : handleAddSubnet}
            initial={subnetDialog.initial}
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
            existingConnections={site.subnetConnections}
          />

          <ConfirmDialog
            open={!!deleteConfirm}
            title="Delete Subnet"
            message={`Delete "${deleteConfirm?.name}"? All containers within will be removed.`}
            onConfirm={handleDeleteSubnet}
            onCancel={() => setDeleteConfirm(null)}
          />
        </>
      )}
    </div>
  );
}
