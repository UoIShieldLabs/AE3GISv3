import { useCallback, useMemo, useState } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { useImmerReducer } from 'use-immer';
import { emptyTopology, type Container } from './types/topology';
import { topologyReducer, type TopologyState } from './store/topologyReducer';
import { TopologyDispatchContext } from './store/TopologyContext';
import { AuthContext, type AuthState } from './store/AuthContext';
import { useCatalogReady } from './catalog/useCatalog';
import { useStatusPolling } from './hooks/useStatusPolling';
import { useTerminalSessions } from './hooks/useTerminalSessions';
import { useDeployment } from './hooks/useDeployment';
import { GeographicView } from './components/GeographicView';
import { SubnetView } from './components/SubnetView';
import { LanView } from './components/LanView';
import { Breadcrumb } from './components/Breadcrumb';
import { NodeInfoPanel } from './components/NodeInfoPanel';
import { TerminalOverlay } from './components/TerminalOverlay';
import { ControlBar } from './components/ControlBar';
import { TopologyBrowser } from './components/TopologyBrowser';
import { LoginScreen } from './components/LoginScreen';
import { PurdueView } from './components/PurdueView';
import * as api from './api/client';

type ViewScale = 'geographic' | 'subnet' | 'lan';

interface NavigationState {
  scale: ViewScale;
  siteId: string | null;
  subnetId: string | null;
}

const GEOGRAPHIC_NAV: NavigationState = { scale: 'geographic', siteId: null, subnetId: null };

const initialState: TopologyState = {
  topology: emptyTopology,
  backendId: null,
  backendName: null,
  deployStatus: 'idle',
  dirty: false,
};

function App() {
  const catalogReady = useCatalogReady();
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [state, dispatch] = useImmerReducer(topologyReducer, initialState);
  const { topology, backendId, backendName, deployStatus, dirty } = state;

  const [loadVersion, setLoadVersion] = useState(0);
  const [nav, setNav] = useState<NavigationState>(GEOGRAPHIC_NAV);
  const [selectedContainer, setSelectedContainer] = useState<Container | null>(null);
  const [browserOpen, setBrowserOpen] = useState(false);
  const [purdueOpen, setPurdueOpen] = useState(false);

  const terminal = useTerminalSessions();
  const polling = useStatusPolling(dispatch);

  const resetView = useCallback(() => {
    setNav(GEOGRAPHIC_NAV);
    setSelectedContainer(null);
    setLoadVersion((v) => v + 1);
  }, []);

  const { busy, handleSave, handleLoad, handleDeploy, handleDestroy, handleNew, handleExport } =
    useDeployment(dispatch, { topology, backendId, backendName, dirty }, polling, resetView);

  // ── Navigation ────────────────────────────────────────────────
  const goToGeographic = useCallback(() => { setNav(GEOGRAPHIC_NAV); setSelectedContainer(null); }, []);
  const goToSite = useCallback((siteId: string) => { setNav({ scale: 'subnet', siteId, subnetId: null }); setSelectedContainer(null); }, []);
  const goToSubnet = useCallback((subnetId: string) => { setNav((p) => ({ ...p, scale: 'lan', subnetId })); setSelectedContainer(null); }, []);

  const effectiveNav = useMemo<NavigationState>(() => {
    const site = topology.sites.find((s) => s.id === nav.siteId);
    if (nav.siteId && !site) return GEOGRAPHIC_NAV;
    if (nav.subnetId && site && !site.subnets.find((s) => s.id === nav.subnetId)) return { ...nav, scale: 'subnet', subnetId: null };
    return nav;
  }, [nav, topology.sites]);

  const currentSite = useMemo(() => topology.sites.find((s) => s.id === effectiveNav.siteId) ?? null, [topology.sites, effectiveNav.siteId]);
  const currentSubnet = useMemo(() => currentSite?.subnets.find((s) => s.id === effectiveNav.subnetId) ?? null, [currentSite, effectiveNav.subnetId]);
  const activeContainer = effectiveNav.scale === 'lan' ? selectedContainer : null;

  const totalContainers = useMemo(
    () => topology.sites.reduce((acc, site) => acc + site.subnets.reduce((a, s) => a + s.containers.length, 0), 0),
    [topology.sites],
  );

  const handleLogin = useCallback((authState: AuthState) => {
    setAuth(authState);
    api.setAuthToken(authState.token);
  }, []);

  const handleLogout = useCallback(() => {
    setAuth(null);
    api.setAuthToken(null);
    polling.stop();
    dispatch({ type: 'LOAD_TOPOLOGY', payload: emptyTopology });
    dispatch({ type: 'CLEAR_BACKEND' });
    resetView();
  }, [dispatch, polling, resetView]);

  const breadcrumbItems = useMemo(() => {
    const items: { label: string; onClick: () => void }[] = [];
    if (effectiveNav.scale !== 'geographic') items.push({ label: 'Network', onClick: goToGeographic });
    if (effectiveNav.scale === 'lan' && currentSite) items.push({ label: currentSite.name, onClick: () => goToSite(currentSite.id) });
    return items;
  }, [effectiveNav.scale, currentSite, goToGeographic, goToSite]);

  const currentLabel = useMemo(() => {
    switch (effectiveNav.scale) {
      case 'geographic': return 'Network Overview';
      case 'subnet': return currentSite?.name ?? 'Site';
      case 'lan': return currentSubnet ? `${currentSubnet.name} (${currentSubnet.cidr})` : 'LAN';
    }
  }, [effectiveNav.scale, currentSite, currentSubnet]);

  const statusLabel = useMemo(() => {
    switch (deployStatus) {
      case 'deployed': return 'Deployed';
      case 'deploying': return 'Deploying...';
      case 'destroying': return 'Destroying...';
      case 'error': return 'Error';
      default: return 'Idle';
    }
  }, [deployStatus]);

  if (!auth) return <LoginScreen onLogin={handleLogin} />;
  if (!catalogReady) return <div style={{ padding: 40, fontFamily: 'monospace' }}>Loading catalog…</div>;

  return (
    <AuthContext.Provider value={auth}>
      <TopologyDispatchContext.Provider value={dispatch}>
        <div className="app-container">
          <div className="scanline-overlay" />
          <header className="header-bar">
            <div className="header-left">
              <div className="header-title">AE3GIS</div>
              <ControlBar
                backendId={backendId}
                backendName={backendName}
                deployStatus={deployStatus}
                dirty={dirty}
                onNew={handleNew}
                onSave={handleSave}
                onLoad={() => setBrowserOpen(true)}
                onExport={handleExport}
                isBusy={busy}
              />
            </div>
            <div className="header-center">
              <div className="header-topo-name">{backendName ?? topology.name ?? 'Untitled Topology'}</div>
              <div className="header-center-row">
                <div className={`control-bar-status status-${deployStatus}`}>
                  <span className="status-dot" />
                  <span>{statusLabel}</span>
                </div>
                <div className="header-stats">
                  <div className="header-stat"><span className="dot" /><span>{topology.sites.length} sites</span></div>
                  <div className="header-stat"><span className="dot" /><span>{totalContainers} containers</span></div>
                </div>
              </div>
            </div>
            <div className="header-right">
              <button className="control-btn btn-deploy" onClick={handleDeploy}
                disabled={busy || !backendId || deployStatus !== 'idle'}
                title={!backendId ? 'Save first to deploy' : 'Deploy with Kathara'}>Deploy</button>
              <button className="control-btn btn-destroy" onClick={handleDestroy}
                disabled={busy || (deployStatus !== 'deployed' && deployStatus !== 'error')}
                title="Destroy running network">Destroy</button>
              <button className="control-btn" onClick={handleLogout} title="Logout">Logout</button>
            </div>
          </header>

          <Breadcrumb items={breadcrumbItems} current={currentLabel} />

          <div className="topology-canvas">
            <ReactFlowProvider>
              {effectiveNav.scale === 'geographic' && (
                <GeographicView topology={topology} onSelectSite={goToSite} autoLayoutTrigger={loadVersion} onPurdue={() => setPurdueOpen(true)} />
              )}
            </ReactFlowProvider>
            <ReactFlowProvider>
              {effectiveNav.scale === 'subnet' && currentSite && (
                <SubnetView site={currentSite} onSelectSubnet={goToSubnet} onOpenRouterTerminal={terminal.open} onPurdue={() => setPurdueOpen(true)} />
              )}
            </ReactFlowProvider>
            <ReactFlowProvider>
              {effectiveNav.scale === 'lan' && currentSubnet && currentSite && (
                <LanView subnet={currentSubnet} siteId={currentSite.id}
                  onSelectContainer={setSelectedContainer} onOpenTerminal={terminal.open}
                  onDeselect={() => setSelectedContainer(null)} onPurdue={() => setPurdueOpen(true)} />
              )}
            </ReactFlowProvider>

            <NodeInfoPanel
              container={activeContainer}
              onClose={() => setSelectedContainer(null)}
              onOpenTerminal={terminal.open}
              siteId={effectiveNav.siteId}
              subnetId={effectiveNav.subnetId}
              topologyId={backendId}
              deployStatus={deployStatus}
            />
          </div>

          {terminal.sessions.length > 0 && terminal.activeId && (
            <TerminalOverlay
              sessions={terminal.sessions}
              activeId={terminal.activeId}
              onActivate={terminal.setActiveId}
              onClose={terminal.close}
              backendId={backendId}
              deployStatus={deployStatus}
              minimized={terminal.minimized}
              onMinimizedChange={terminal.setMinimized}
            />
          )}

          <TopologyBrowser open={browserOpen} onClose={() => setBrowserOpen(false)} onLoad={handleLoad} currentId={backendId} />
          <PurdueView open={purdueOpen} onClose={() => setPurdueOpen(false)} topology={topology} />
        </div>
      </TopologyDispatchContext.Provider>
    </AuthContext.Provider>
  );
}

export default App;
