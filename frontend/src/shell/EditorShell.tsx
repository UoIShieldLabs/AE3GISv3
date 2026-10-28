import { useEffect } from 'react';
import { usePanelRef } from 'react-resizable-panels';
import { useAppShallow } from '@/store/selectors';
import { ResizableGroup, ResizableHandle, ResizablePanel } from '@/ui';

/** Width the right column grows to (if narrower) when tutorials open. */
const TUTORIALS_MIN_WIDTH = 380;

export interface EditorShellProps {
  topBar: React.ReactNode;
  breadcrumb: React.ReactNode;
  /** Optional strip under the breadcrumb (e.g. images that still need building). */
  notice?: React.ReactNode;
  canvas: React.ReactNode;
  sidebar?: React.ReactNode;
  inspector?: React.ReactNode;
  /** Shown above the inspector in the right column while tutorials are open. */
  tutorials?: React.ReactNode;
  dock?: React.ReactNode;
  statusBar?: React.ReactNode;
}

/** Fixed frame: top bar / [sidebar | breadcrumb + canvas + dock | tutorials over inspector] / status bar. */
export function EditorShell({ topBar, breadcrumb, notice, canvas, sidebar, inspector, tutorials, dock, statusBar }: EditorShellProps) {
  const { sidebarOpen, inspectorOpen, tutorialsOpen, dockMode } = useAppShallow((s) => ({
    sidebarOpen: s.sidebarOpen,
    inspectorOpen: s.inspectorOpen,
    tutorialsOpen: s.tutorialsOpen,
    dockMode: s.dockTabs.length === 0 ? 'hidden' : s.dockMinimized ? 'minimized' : 'open',
  }));
  const showSidebar = !!sidebar && sidebarOpen;
  const showInspector = !!inspector && inspectorOpen;
  const showTutorials = !!tutorials && tutorialsOpen;
  const rightRef = usePanelRef();

  // A notebook wants a little more room than the inspector's default.
  useEffect(() => {
    if (!showTutorials) return;
    const panel = rightRef.current;
    const width = panel?.getSize().inPixels ?? 0;
    if (panel && width && width < TUTORIALS_MIN_WIDTH) panel.resize(TUTORIALS_MIN_WIDTH);
  }, [showTutorials, rightRef]);

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
            {notice}
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
        {showInspector || showTutorials ? (
          <>
            <ResizableHandle id="h-inspector" />
            <ResizablePanel id="inspector" panelRef={rightRef} defaultSize={showTutorials ? TUTORIALS_MIN_WIDTH : 320} minSize={260} maxSize={640}>
              {/* One structure for every combination, so toggling one section never remounts the other. */}
              <ResizableGroup orientation="vertical" className="min-h-0">
                {showTutorials ? (
                  <>
                    <ResizablePanel id="tutorials" defaultSize="60%" minSize={160} className="border-l border-border">{tutorials}</ResizablePanel>
                    {showInspector ? <ResizableHandle id="v-right" /> : null}
                  </>
                ) : null}
                {showInspector ? <ResizablePanel id="inspector-body" minSize={120}>{inspector}</ResizablePanel> : null}
              </ResizableGroup>
            </ResizablePanel>
          </>
        ) : null}
      </ResizableGroup>
      {statusBar ? <footer className="flex h-6 shrink-0 items-center border-t border-border bg-surface px-3 text-2xs text-fg-muted">{statusBar}</footer> : null}
    </div>
  );
}
