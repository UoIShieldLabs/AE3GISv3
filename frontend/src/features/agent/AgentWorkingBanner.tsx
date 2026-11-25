import { MessageSquare, Square } from 'lucide-react';
import { editorLocked, useAppStore } from '@/store';
import { Button, Spinner } from '@/ui';
import { openChat, stopRun } from './actions';

/** Under the breadcrumb while an agent run works in the open topology: editing
 *  is paused, its changes arrive live. */
export function AgentWorkingBanner() {
  const lock = useAppStore((s) => (editorLocked(s) ? s.agentLock : null));
  if (!lock) return null;
  return (
    <div className="ae-agent-banner flex h-9 shrink-0 items-center gap-2 border-b border-border bg-accent-soft px-3 text-xs text-fg" role="status">
      <Spinner className="size-3.5 text-accent" />
      <span className="truncate">The agent is working on this topology. Editing is paused; its changes appear as it makes them.</span>
      <span className="ml-auto flex shrink-0 gap-1.5">
        <Button size="xs" variant="ghost" onClick={() => void openChat(lock.chatId)}>
          <MessageSquare /> Chat
        </Button>
        <Button size="xs" variant="danger-soft" onClick={() => void stopRun(lock.chatId)}>
          <Square /> Stop
        </Button>
      </span>
    </div>
  );
}
