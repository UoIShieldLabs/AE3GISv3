import { Sparkles } from 'lucide-react';

/** The agent's icon, in one place. */
export function AgentMark({ className }: { className?: string }) {
  return <Sparkles className={className} aria-hidden />;
}
