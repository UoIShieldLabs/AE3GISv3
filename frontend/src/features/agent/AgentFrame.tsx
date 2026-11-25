import { Suspense, lazy, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { setLockedEditHandler, useAppStore } from '@/store';
import { ResizableGroup, ResizableHandle, ResizablePanel, Spinner, toast } from '@/ui';
import { hasMod } from '@/lib/keyboard';
import { loadAgentStatus, loadChats } from './actions';
import { useAgentStore } from './agentStore';
import { setAgentNavigator } from './uiActions';

// The panel (and Markdown with it) loads when it first opens.
const AgentPanel = lazy(() => import('./AgentPanel').then((m) => ({ default: m.AgentPanel })));

/** Every signed-in page, with the agent panel on the right when it's open. One
 *  structure whether it is or not, so opening it never remounts the page. */
export function AgentFrame({ children }: { children: React.ReactNode }) {
  const open = useAppStore((s) => s.agentOpen);
  const mode = useAgentStore((s) => s.status?.mode ?? null);
  const navigate = useNavigate();

  useEffect(() => {
    setAgentNavigator((to) => void navigate(to));
  }, [navigate]);

  useEffect(() => {
    void loadAgentStatus();
  }, []);

  useEffect(() => {
    if (mode) void loadChats();
  }, [mode]);

  useEffect(() => {
    setLockedEditHandler(() =>
      toast.info('The agent is working on this topology', {
        id: 'agent-lock',
        description: 'Editing is paused until it finishes. Stop it from the banner or the chat to edit now.',
      }),
    );
    return () => setLockedEditHandler(null);
  }, []);

  // ⌘J opens and closes the panel, anywhere.
  useEffect(() => {
    if (!mode) return;
    const onKey = (e: KeyboardEvent) => {
      if (hasMod(e) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'j') {
        e.preventDefault();
        useAppStore.getState().toggleAgent();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mode]);

  const show = open && !!mode;
  return (
    <ResizableGroup orientation="horizontal" className="h-full w-full">
      <ResizablePanel id="app-main" minSize={480}>
        {children}
      </ResizablePanel>
      {show ? (
        <>
          <ResizableHandle id="h-agent" />
          <ResizablePanel id="agent" defaultSize={400} minSize={320} maxSize={760}>
            <Suspense
              fallback={
                <div className="flex h-full items-center justify-center border-l border-border bg-surface">
                  <Spinner />
                </div>
              }
            >
              <AgentPanel />
            </Suspense>
          </ResizablePanel>
        </>
      ) : null}
    </ResizableGroup>
  );
}
