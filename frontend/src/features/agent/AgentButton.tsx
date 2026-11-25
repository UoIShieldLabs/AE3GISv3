import { useAppStore } from '@/store';
import { IconButton } from '@/ui';
import { MOD } from '@/lib/keyboard';
import { cn } from '@/lib/cn';
import { useAgentStore } from './agentStore';
import { AgentMark } from './AgentMark';

/** Opens and closes the agent panel (hidden when the caller has no agent). A dot
 *  while one of their runs is going. */
export function AgentButton() {
  const open = useAppStore((s) => s.agentOpen);
  const mode = useAgentStore((s) => s.status?.mode ?? null);
  const busy = useAgentStore((s) => Object.values(s.byId).some((c) => !!c.run));
  if (!mode) return null;
  const label = mode === 'tutor' ? 'Tutor' : 'Agent';
  return (
    <IconButton
      label={open ? `Hide the ${label.toLowerCase()}` : `Ask the ${label.toLowerCase()}`}
      shortcut={`${MOD}J`}
      size="icon-sm"
      variant={open ? 'secondary' : 'ghost'}
      onClick={() => useAppStore.getState().toggleAgent()}
      className="relative"
    >
      <AgentMark />
      <span className={cn('absolute right-1 top-1 size-1.5 rounded-full bg-accent', !busy && 'hidden')} />
    </IconButton>
  );
}
