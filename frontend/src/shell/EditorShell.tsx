import { useAppShallow } from '@/store/selectors';
import { ResizableGroup, ResizableHandle, ResizablePanel } from '@/ui';

export interface EditorShellProps {
  topBar: React.ReactNode;
  breadcrumb: React.ReactNode;
  canvas: React.ReactNode;
  sidebar?: React.ReactNode;
  inspector?: React.ReactNode;
  dock?: React.ReactNode;
  statusBar?: React.ReactNode;
}

/** Fixed frame: top bar / [sidebar | breadcrumb + canvas + dock | inspector] / status bar. */
export function EditorShell({ topBar, breadcrumb, canvas, sidebar, inspector, dock, statusBar }: EditorShellProps) {
  const { sidebarOpen, inspectorOpen, dockMode } = useAppShallow((s) => ({
    sidebarOpen: s.sidebarOpen,
    inspectorOpen: s.inspectorOpen,
    dockMode: s.terminals.length === 0 ? 'hidden' : s.terminalMinimized ? 'minimized' : 'open',
  }));
  const showSidebar = !!sidebar && sidebarOpen;
  const showInspector = !!inspector && inspectorOpen;

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-app text-fg">
      <header className="flex h-12 shrink-0 items-center border-b border-border bg-surface px-2">{topBar}</header>
      <ResizableGroup orientation="horizontal" className="min-h-0 flex-1">
        {showSidebar ? (
          <>
            <ResizablePanel id="sidebar" defaultSize={272} minSize={220} maxSize={440}>{sidebar}</ResizablePanel>
            <ResizableHandle id="h-sidebar" />
          </>
        ) : null}
        <ResizablePanel id="main" minSize={360}>
          <main className="flex h-full min-w-0 flex-col">
            <div className="flex h-9 shrink-0 items-center border-b border-border bg-surface px-2">{breadcrumb}</div>
            <ResizableGroup orientation="vertical" className="min-h-0 flex-1">
              <ResizablePanel id="canvas" minSize={160}>{canvas}</ResizablePanel>
              {dock && dockMode === 'open' ? (
                <>
                  <ResizableHandle id="h-dock" />
                  <ResizablePanel id="dock" defaultSize={280} minSize={120} maxSize="75%">{dock}</ResizablePanel>
                </>
              ) : null}
            </ResizableGroup>
            {dock && dockMode === 'minimized' ? <div className="h-8 shrink-0">{dock}</div> : null}
          </main>
        </ResizablePanel>
        {showInspector ? (
          <>
            <ResizableHandle id="h-inspector" />
            <ResizablePanel id="inspector" defaultSize={320} minSize={260} maxSize={560}>{inspector}</ResizablePanel>
          </>
        ) : null}
      </ResizableGroup>
      {statusBar ? <footer className="flex h-6 shrink-0 items-center border-t border-border bg-surface px-3 text-2xs text-fg-muted">{statusBar}</footer> : null}
    </div>
  );
}
