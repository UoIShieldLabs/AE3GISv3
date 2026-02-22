import { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { SiteNode } from './nodes/SiteNode';
import { NeonEdgeStraight } from './edges/NeonEdge';
import { ContextMenu, type ContextMenuItem } from './ui/ContextMenu';
import { Toolbar } from './Toolbar';
import { SiteDialog } from './dialogs/SiteDialog';
import { ConnectionDialog } from './dialogs/ConnectionDialog';
import { BulkConnectionDialog } from './dialogs/BulkConnectionDialog';
import { ConfirmDialog } from './dialogs/ConfirmDialog';
import { TopologyDispatchContext } from '../store/TopologyContext';
import { computeLayout } from '../utils/autoLayout';
import { generateId } from '../utils/idGenerator';
import type { TopologyData, Site } from '../data/sampleTopology';

const nodeTypes = { site: SiteNode };
const edgeTypes = { neonStraight: NeonEdgeStraight };

interface GeographicViewProps {
  topology: TopologyData;
  onSelectSite: (siteId: string) => void;
  readOnly?: boolean;
}

export function GeographicView({ topology, onSelectSite, readOnly }: GeographicViewProps) {
  const dispatch = useContext(TopologyDispatchContext);
  const { fitView } = useReactFlow();

  // Context menu state
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; items: ContextMenuItem[] } | null>(null);

  // Dialog state
  const [siteDialog, setSiteDialog] = useState<{ open: boolean; initial?: Site }>({ open: false });
  const [connDialog, setConnDialog] = useState(false);
  const [bulkConnDialog, setBulkConnDialog] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ siteId: string; name: string } | null>(null);

  const handleDrillDown = useCallback(
    (siteId: string) => onSelectSite(siteId),
    [onSelectSite]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Sync nodes with topology data
  useEffect(() => {
    setNodes(
      topology.sites.map((site) => ({
        id: site.id,
        type: 'site',
        position: { x: site.position.x * 3, y: site.position.y * 2.5 },
        data: {
          label: site.name,
          location: site.location,
          subnetCount: site.subnets.length,
          containerCount: site.subnets.reduce(
            (acc, s) => acc + s.containers.length,
            0
          ),
          onDrillDown: handleDrillDown,
        },
      }))
    );
  }, [topology.sites, handleDrillDown, setNodes]);

  // Sync edges with topology data
  useEffect(() => {
    setEdges(
      topology.siteConnections.map((conn, i) => ({
        id: `site-edge-${i}`,
        source: conn.from,
        target: conn.to,
        type: 'neonStraight',
        label: conn.label,
        data: { color: '#00ff9f' },
      }))
    );
  }, [topology.siteConnections, setEdges]);



  // Context menu handlers
  const onPaneContextMenu = useCallback((event: MouseEvent | React.MouseEvent) => {
    event.preventDefault();
    setCtxMenu({
      x: event.clientX,
      y: event.clientY,
      items: [
        { label: 'Add Site', onClick: () => setSiteDialog({ open: true }) },
        { label: 'Add Connection', onClick: () => setConnDialog(true) },
        { label: 'Bulk Add Connections', onClick: () => setBulkConnDialog(true) },
      ],
    });
  }, []);

  const onNodeContextMenu = useCallback((event: React.MouseEvent, node: Node) => {
    event.preventDefault();
    const site = topology.sites.find(s => s.id === node.id);
    if (!site) return;
    setCtxMenu({
      x: event.clientX,
      y: event.clientY,
      items: [
        { label: 'Edit Site', onClick: () => setSiteDialog({ open: true, initial: site }) },
        { label: 'Delete Site', onClick: () => setDeleteConfirm({ siteId: site.id, name: site.name }), danger: true },
      ],
    });
  }, [topology.sites]);

  const onEdgeContextMenu = useCallback((event: React.MouseEvent, edge: Edge) => {
    event.preventDefault();
    const conn = topology.siteConnections[Number(edge.id.replace('site-edge-', ''))];
    if (!conn) return;
    setCtxMenu({
      x: event.clientX,
      y: event.clientY,
      items: [
        {
          label: 'Delete Connection',
          danger: true,
          onClick: () => dispatch({ type: 'DELETE_SITE_CONNECTION', payload: { from: conn.from, to: conn.to } }),
        },
      ],
    });
  }, [topology.siteConnections, dispatch]);

  // CRUD handlers
  const handleAddSite = useCallback((data: { name: string; location: string; posX: number; posY: number }) => {
    dispatch({
      type: 'ADD_SITE',
      payload: {
        id: generateId(),
        name: data.name,
        location: data.location,
        position: { x: data.posX, y: data.posY },
        subnets: [],
        subnetConnections: [],
      },
    });
  }, [dispatch]);

  const handleEditSite = useCallback((data: { name: string; location: string; posX: number; posY: number }) => {
    if (!siteDialog.initial) return;
    dispatch({
      type: 'UPDATE_SITE',
      payload: {
        siteId: siteDialog.initial.id,
        updates: {
          name: data.name,
          location: data.location,
          position: { x: data.posX, y: data.posY },
        },
      },
    });
  }, [dispatch, siteDialog.initial]);

  const handleDeleteSite = useCallback(() => {
    if (!deleteConfirm) return;
    dispatch({ type: 'DELETE_SITE', payload: { siteId: deleteConfirm.siteId } });
    setDeleteConfirm(null);
  }, [dispatch, deleteConfirm]);

  const handleAddConnection = useCallback((data: { from: string; to: string; label: string }) => {
    dispatch({
      type: 'ADD_SITE_CONNECTION',
      payload: { from: data.from, to: data.to, label: data.label || undefined },
    });
  }, [dispatch]);

  const handleBulkConnections = useCallback((connections: { from: string; to: string }[]) => {
    for (const conn of connections) {
      dispatch({
        type: 'ADD_SITE_CONNECTION',
        payload: { from: conn.from, to: conn.to },
      });
    }
  }, [dispatch]);

  // Interactive edge connection
  const onConnect = useCallback((params: Connection) => {
    if (params.source && params.target) {
      dispatch({
        type: 'ADD_SITE_CONNECTION',
        payload: { from: params.source, to: params.target },
      });
    }
  }, [dispatch]);

  // Persist drag positions
  const onNodeDragStop = useCallback((_: React.MouseEvent, node: Node) => {
    dispatch({
      type: 'UPDATE_SITE',
      payload: {
        siteId: node.id,
        updates: { position: { x: node.position.x / 3, y: node.position.y / 2.5 } },
      },
    });
  }, [dispatch]);

  // Auto-layout
  const handleAutoLayout = useCallback(() => {
    const positions = computeLayout(
      topology.sites.map(s => ({ id: s.id, width: 120, height: 100 })),
      topology.siteConnections.map(c => ({ source: c.from, target: c.to })),
      { direction: 'LR', nodeSpacing: 100, rankSpacing: 150 }
    );
    for (const [siteId, pos] of positions) {
      dispatch({
        type: 'UPDATE_SITE',
        payload: { siteId, updates: { position: { x: pos.x / 3, y: pos.y / 2.5 } } },
      });
    }
    setTimeout(() => fitView({ padding: 0.3 }), 50);
  }, [topology.sites, topology.siteConnections, dispatch, fitView]);

  const connectionNodes = useMemo(
    () => topology.sites.map(s => ({ id: s.id, name: s.name })),
    [topology.sites]
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
        maxZoom={2}
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
        connectionLineStyle={{ stroke: '#00ff9f', strokeWidth: 1.5, opacity: 0.6 }}
      >
        <Background
          color="rgba(0, 255, 159, 0.06)"
          gap={40}
          size={1}
        />
        <Controls
          showInteractive={false}
          style={{ bottom: 20, right: 20 }}
        />
        <MiniMap
          nodeColor="#00ff9f"
          maskColor="rgba(10, 10, 15, 0.8)"
          style={{ bottom: 20, left: 20, width: 140, height: 100 }}
        />
      </ReactFlow>

      <Toolbar
        onAdd={() => setSiteDialog({ open: true })}
        addLabel="Site"
        onAutoLayout={handleAutoLayout}
        readOnly={readOnly}
      />

      <div className="scale-label">Geographic Overview</div>

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
          <SiteDialog
            open={siteDialog.open}
            onClose={() => setSiteDialog({ open: false })}
            onSubmit={siteDialog.initial ? handleEditSite : handleAddSite}
            initial={siteDialog.initial}
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
            existingConnections={topology.siteConnections}
          />

          <ConfirmDialog
            open={!!deleteConfirm}
            title="Delete Site"
            message={`Delete "${deleteConfirm?.name}"? All subnets and containers within will be removed.`}
            onConfirm={handleDeleteSite}
            onCancel={() => setDeleteConfirm(null)}
          />
        </>
      )}
    </div>
  );
}
