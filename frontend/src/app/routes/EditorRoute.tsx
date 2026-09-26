import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useAppStore } from '@/store';
import { ROOT_SCOPE, defaultScopeFor, resolveScope, scopeEquals, scopePath, type Scope } from '@/lib/topology';
import { createNewTopology, deployTopology, destroyTopology, exportLab, exportTopologyJson, loadTopology, saveTopology } from '@/features/deployment/actions';
import { useServerValidation } from '@/features/deployment/useServerValidation';
import { UnsavedChangesGuard } from '@/features/topology/UnsavedChangesGuard';
import { AddEntityProvider } from '@/features/topology/AddEntityProvider';
import { Dock } from '@/features/dock/Dock';
import { PurdueSheet } from '@/features/purdue/PurdueSheet';
import { ImagesSheet } from '@/features/images/ImagesSheet';
import { StartCaptureDialog } from '@/features/capture/StartCaptureDialog';
import { RunsSheet } from '@/features/runs/RunsSheet';
import { RequiredImagesBanner } from '@/features/images/RequiredImagesBanner';
import { TopologyCanvas } from '@/canvas/TopologyCanvas';
import { EditorShell } from '@/shell/EditorShell';
import { TopBar } from '@/shell/TopBar';
import { Breadcrumb } from '@/shell/Breadcrumb';
import { Sidebar } from '@/shell/Sidebar';
import { Inspector } from '@/shell/Inspector';
import { StatusBar } from '@/shell/StatusBar';
import { CommandPalette } from '@/shell/CommandPalette';
import { Spinner } from '@/ui';

export function EditorRoute() {
  const { topologyId = 'draft', siteId, subnetId } = useParams();
  const navigate = useNavigate();
  const backendId = useAppStore((s) => s.backendId);
  const topology = useAppStore((s) => s.topology);
  const inflight = useRef<string | null>(null);
  useServerValidation();

  const isDraft = topologyId === 'draft';
  const ready = isDraft ? backendId === null : backendId === topologyId;

  // Make sure the topology in the store matches the URL.
  useEffect(() => {
    if (ready || inflight.current === topologyId) return;
    if (isDraft) {
      createNewTopology();
      return;
    }
    inflight.current = topologyId;
    const openedAtRoot = !siteId;
    void loadTopology(topologyId).then((ok) => {
      if (inflight.current === topologyId) inflight.current = null;
      if (!ok) {
        void navigate('/', { replace: true });
        return;
      }
      // Fresh open at the root URL: jump to the deepest single-child scope.
      if (openedAtRoot) {
        const def = defaultScopeFor(useAppStore.getState().topology);
        if (def.level !== 'root') void navigate(scopePath(topologyId, def), { replace: true });
      }
    });
    // `siteId` is only read at effect time to decide the auto-open; not a trigger.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topologyId, isDraft, ready, navigate]);

  const requested = useMemo<Scope>(
    () => (siteId && subnetId ? { level: 'subnet', siteId, subnetId } : siteId ? { level: 'site', siteId } : ROOT_SCOPE),
    [siteId, subnetId],
  );
  const scope = useMemo(() => (ready ? resolveScope(topology, requested) : requested), [ready, topology, requested]);

  // A stale deep link (deleted site/subnet) falls back up the chain.
  useEffect(() => {
    if (ready && !scopeEquals(scope, requested)) void navigate(scopePath(topologyId, scope), { replace: true });
  }, [ready, scope, requested, topologyId, navigate]);

  const onNavigate = useCallback((s: Scope) => { void navigate(scopePath(topologyId, s)); }, [navigate, topologyId]);

  const save = useCallback(async () => {
    const id = await saveTopology();
    if (id && isDraft) void navigate(scopePath(id, scope), { replace: true });
    return !!id;
  }, [isDraft, navigate, scope]);

  if (!ready) {
    return (
      <div className="flex h-full items-center justify-center bg-app">
        <Spinner />
      </div>
    );
  }

  return (
    <AddEntityProvider>
      <EditorShell
        topBar={
          <TopBar
            onSave={() => void save()}
            onExport={exportTopologyJson}
            onExportLab={(f) => void exportLab(f)}
            onDeploy={() => void deployTopology()}
            onDestroy={() => void destroyTopology()}
            onLibrary={() => void navigate('/')}
          />
        }
        breadcrumb={<Breadcrumb scope={scope} onNavigate={onNavigate} />}
        notice={<RequiredImagesBanner />}
        sidebar={<Sidebar scope={scope} onNavigate={onNavigate} />}
        canvas={<TopologyCanvas scope={scope} onNavigate={onNavigate} onSave={() => void save()} />}
        inspector={<Inspector scope={scope} onNavigate={onNavigate} />}
        dock={<Dock />}
        statusBar={<StatusBar scope={scope} />}
      />
      <PurdueSheet />
      <ImagesSheet />
      <RunsSheet />
      <StartCaptureDialog />
      <CommandPalette scope={scope} onNavigate={onNavigate} onSave={() => void save()} />
      <UnsavedChangesGuard onSave={save} />
    </AddEntityProvider>
  );
}
