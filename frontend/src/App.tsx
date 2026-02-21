import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { useImmerReducer } from 'use-immer';
import { sampleTopology, type Container } from './data/sampleTopology';
import { topologyReducer, type TopologyState } from './store/topologyReducer';
import { TopologyDispatchContext } from './store/TopologyContext';
import { GeographicView } from './components/GeographicView';
import { SubnetView } from './components/SubnetView';
import { LanView } from './components/LanView';
import { Breadcrumb } from './components/Breadcrumb';
import { NodeInfoPanel } from './components/NodeInfoPanel';
import { TerminalOverlay } from './components/TerminalOverlay';
import { ControlBar } from './components/ControlBar';
import { TopologyBrowser } from './components/TopologyBrowser';
import * as api from './api/client';
import { deploymentName } from './utils/deploymentName';

type ViewScale = 'geographic' | 'subnet' | 'lan';

interface NavigationState {
  scale: ViewScale;
  siteId: string | null;
  subnetId: string | null;
}

const initialState: TopologyState = {
  topology: sampleTopology,
  backendId: null,
  backendName: null,
  deployStatus: 'idle',
  dirty: false,
};

function App() {
  const [state, dispatch] = useImmerReducer(topologyReducer, initialState);
  const { topology, backendId, backendName, deployStatus, dirty } = state;

  const [nav, setNav] = useState<NavigationState>({
    scale: 'geographic',
    siteId: null,
    subnetId: null,
  });

  const [selectedContainer, setSelectedContainer] = useState<Container | null>(null);
  const [terminalContainer, setTerminalContainer] = useState<Container | null>(null);
  const [browserOpen, setBrowserOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);

  // ── Navigation handlers ────────────────────────────────────────

  const goToGeographic = useCallback(() => {
    setNav({ scale: 'geographic', siteId: null, subnetId: null });
    setSelectedContainer(null);
  }, []);

  const goToSite = useCallback((siteId: string) => {
    setNav({ scale: 'subnet', siteId, subnetId: null });
    setSelectedContainer(null);
  }, []);

  const goToSubnet = useCallback(
    (subnetId: string) => {
      setNav((prev) => ({ ...prev, scale: 'lan', subnetId }));
      setSelectedContainer(null);
    },
    []
  );

  // Navigation guards
  const effectiveNav = useMemo<NavigationState>(() => {
    if (nav.siteId && !topology.sites.find(s => s.id === nav.siteId)) {
      return { scale: 'geographic', siteId: null, subnetId: null };
    }
    const site = topology.sites.find(s => s.id === nav.siteId);
    if (nav.subnetId && site && !site.subnets.find(s => s.id === nav.subnetId)) {
      return { ...nav, scale: 'subnet', subnetId: null };
    }
    return nav;
  }, [nav, topology.sites]);

  const currentSite = useMemo(
    () => topology.sites.find((s) => s.id === effectiveNav.siteId) ?? null,
    [topology.sites, effectiveNav.siteId]
  );

  const currentSubnet = useMemo(
    () => currentSite?.subnets.find((s) => s.id === effectiveNav.subnetId) ?? null,
    [currentSite, effectiveNav.subnetId]
  );

  const activeContainer = useMemo(
    () => (effectiveNav.scale === 'lan' ? selectedContainer : null),
    [effectiveNav.scale, selectedContainer]
  );

  const totalContainers = useMemo(
    () =>
      topology.sites.reduce(
        (acc, site) =>
          acc + site.subnets.reduce((a, s) => a + s.containers.length, 0),
        0
      ),
    [topology.sites]
  );

  // ── WebSocket management ──────────────────────────────────────

  const connectWebSocket = useCallback((topoId: string, topoName: string) => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/topologies/ws/${topoId}/status`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const containers: api.ClabContainer[] = data.containers || [];
        // Map clab container names → frontend container IDs
        // clab names are prefixed with "clab-{topo_name}-"
        const prefix = `clab-${topoName}-`;
        const statuses: Record<string, 'running' | 'stopped' | 'paused'> = {};
        for (const c of containers) {
          const id = c.name.startsWith(prefix)
            ? c.name.slice(prefix.length)
            : c.name;
          const state = c.state?.toLowerCase();
          if (state === 'running') statuses[id] = 'running';
          else if (state === 'paused') statuses[id] = 'paused';
          else statuses[id] = 'stopped';
        }
        dispatch({ type: 'UPDATE_CONTAINER_STATUSES', payload: { statuses } });
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      // Only clear ref if this is still the active connection
      if (wsRef.current === ws) wsRef.current = null;
    };

    wsRef.current = ws;
  }, [dispatch]);

  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // ── Backend handlers ──────────────────────────────────────────

  const handleSave = useCallback(async (name?: string) => {
    setBusy(true);
    try {
      if (backendId) {
        // Update existing
        await api.updateTopology(backendId, backendName ?? undefined, topology);
        dispatch({ type: 'MARK_CLEAN' });
      } else {
        // Create new — name is required
        const topoName = name || 'Untitled Topology';
        const record = await api.createTopology(topoName, topology);
        dispatch({
          type: 'SET_BACKEND_INFO',
          payload: { id: record.id, name: record.name, status: record.status },
        });
        dispatch({ type: 'MARK_CLEAN' });
      }
    } catch (err) {
      console.error('Save failed:', err);
    } finally {
      setBusy(false);
    }
  }, [backendId, backendName, topology, dispatch]);

  const handleLoad = useCallback(async (id: string) => {
    setBusy(true);
    try {
      const record = await api.getTopology(id);
      dispatch({ type: 'LOAD_TOPOLOGY', payload: record.data });
      dispatch({
        type: 'SET_BACKEND_INFO',
        payload: { id: record.id, name: record.name, status: record.status },
      });
      // Reset navigation
      setNav({ scale: 'geographic', siteId: null, subnetId: null });
      setSelectedContainer(null);
      // If deployed, connect WebSocket
      if (record.status === 'deployed') {
        const topoName = deploymentName(record.id, record.data.name);
        connectWebSocket(record.id, topoName);
      } else {
        disconnectWebSocket();
      }
    } catch (err) {
      console.error('Load failed:', err);
    } finally {
      setBusy(false);
    }
  }, [dispatch, connectWebSocket, disconnectWebSocket]);

  const handleDeploy = useCallback(async () => {
    if (!backendId) return;
    setBusy(true);
    try {
      // Auto-save if dirty
      if (dirty) {
        await api.updateTopology(backendId, backendName ?? undefined, topology);
        dispatch({ type: 'MARK_CLEAN' });
      }
      // Ensure the generated YAML reflects latest backend generator logic.
      await api.generateTopology(backendId);
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'deploying' });
      await api.deployTopology(backendId);
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'deployed' });
      // Connect WebSocket for live status
      const topoName = deploymentName(backendId, topology.name);
      connectWebSocket(backendId, topoName);
    } catch (err) {
      console.error('Deploy failed:', err);
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'error' });
    } finally {
      setBusy(false);
    }
  }, [backendId, backendName, dirty, topology, dispatch, connectWebSocket]);

  const handleDestroy = useCallback(async () => {
    if (!backendId) return;
    setBusy(true);
    try {
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'destroying' });
      await api.destroyTopology(backendId);
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'idle' });
      disconnectWebSocket();
    } catch (err) {
      console.error('Destroy failed:', err);
      dispatch({ type: 'SET_DEPLOY_STATUS', payload: 'error' });
    } finally {
      setBusy(false);
    }
  }, [backendId, dispatch, disconnectWebSocket]);

  const handleNew = useCallback(() => {
    dispatch({ type: 'LOAD_TOPOLOGY', payload: { sites: [], siteConnections: [] } });
    dispatch({ type: 'CLEAR_BACKEND' });
    setNav({ scale: 'geographic', siteId: null, subnetId: null });
    setSelectedContainer(null);
    disconnectWebSocket();
  }, [dispatch, disconnectWebSocket]);

  const handleExport = useCallback(() => {
    const json = JSON.stringify(topology, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${topology.name || 'topology'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [topology]);

  // ── Breadcrumbs ───────────────────────────────────────────────

  const breadcrumbItems = useMemo(() => {
    const items: { label: string; onClick: () => void }[] = [];
    if (effectiveNav.scale !== 'geographic') {
      items.push({ label: 'Network', onClick: goToGeographic });
    }
    if (effectiveNav.scale === 'lan' && currentSite) {
      items.push({
        label: currentSite.name,
        onClick: () => goToSite(currentSite.id),
      });
    }
    return items;
  }, [effectiveNav.scale, currentSite, goToGeographic, goToSite]);

  const currentLabel = useMemo(() => {
    switch (effectiveNav.scale) {
      case 'geographic':
        return 'Network Overview';
      case 'subnet':
        return currentSite?.name ?? 'Site';
      case 'lan':
        return currentSubnet
          ? `${currentSubnet.name} (${currentSubnet.cidr})`
          : 'LAN';
    }
  }, [effectiveNav.scale, currentSite, currentSubnet]);

  // ── Render ────────────────────────────────────────────────────

  return (
    <TopologyDispatchContext.Provider value={dispatch}>
      <div className="app-container">
        {/* Scanline overlay for CRT effect */}
        <div className="scanline-overlay" />

        {/* Header */}
        <header className="header-bar">
          <div className="header-title">AE3GIS</div>
          <div className="header-stats">
            <div className="header-stat">
              <span className="dot" />
              <span>{topology.sites.length} sites</span>
            </div>
            <div className="header-stat">
              <span className="dot" />
              <span>{totalContainers} containers</span>
            </div>
          </div>
          <ControlBar
            backendId={backendId}
            backendName={backendName}
            deployStatus={deployStatus}
            dirty={dirty}
            onNew={handleNew}
            onSave={handleSave}
            onLoad={() => setBrowserOpen(true)}
            onDeploy={handleDeploy}
            onDestroy={handleDestroy}
            onExport={handleExport}
            isBusy={busy}
          />
        </header>

        {/* Breadcrumb navigation */}
        <Breadcrumb items={breadcrumbItems} current={currentLabel} />

        {/* Main canvas */}
        <div className="topology-canvas">
          <div className="canvas-main">
            <ReactFlowProvider>
              {effectiveNav.scale === 'geographic' && (
                <GeographicView
                  topology={topology}
                  onSelectSite={goToSite}
                />
              )}
            </ReactFlowProvider>

            <ReactFlowProvider>
              {effectiveNav.scale === 'subnet' && currentSite && (
                <SubnetView
                  site={currentSite}
                  onSelectSubnet={goToSubnet}
                />
              )}
            </ReactFlowProvider>

            <ReactFlowProvider>
              {effectiveNav.scale === 'lan' && currentSubnet && currentSite && (
                <LanView
                  subnet={currentSubnet}
                  siteId={currentSite.id}
                  onSelectContainer={setSelectedContainer}
                  onOpenTerminal={setTerminalContainer}
                  onDeselect={() => setSelectedContainer(null)}
                />
              )}
            </ReactFlowProvider>

            {/* Info panel */}
            <NodeInfoPanel
              container={activeContainer}
              onClose={() => setSelectedContainer(null)}
              onOpenTerminal={(c) => setTerminalContainer(c)}
              siteId={effectiveNav.siteId}
              subnetId={effectiveNav.subnetId}
            />
          </div>

          {/* Terminal panel */}
          {terminalContainer && (
            <TerminalOverlay
              container={terminalContainer}
              backendId={backendId}
              deployStatus={deployStatus}
              topoName={backendId ? deploymentName(backendId, topology.name) : (topology.name || 'ae3gis-topology')}
              onClose={() => setTerminalContainer(null)}
            />
          )}
        </div>

        {/* Topology browser dialog */}
        <TopologyBrowser
          open={browserOpen}
          onClose={() => setBrowserOpen(false)}
          onLoad={handleLoad}
          currentId={backendId}
        />
      </div>
    </TopologyDispatchContext.Provider>
  );
}

export default App;
