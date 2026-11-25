import { useEffect, useState } from 'react';
import { MessageSquare } from 'lucide-react';
import * as api from '@/api/client';
import { ago } from '@/lib/time';
import { openChat } from './actions';
import { useAgentStore } from './agentStore';
import { AgentMark } from './AgentMark';

/** On a student's page (staff): their chats with the tutor, opened read-only in
 *  the agent panel. Nothing when the agent isn't configured. */
export function StudentChats({ studentId, username }: { studentId: string; username: string }) {
  const agentOn = useAgentStore((s) => !!s.status?.enabled);
  const [chats, setChats] = useState<api.AgentChat[] | null>(null);

  useEffect(() => {
    if (!agentOn) return;
    let live = true;
    api
      .listAgentChats({ owner: studentId })
      .then((c) => live && setChats(c))
      .catch(() => live && setChats([]));
    return () => {
      live = false;
    };
  }, [agentOn, studentId]);

  if (!agentOn || !chats || chats.length === 0) return null;
  return (
    <section aria-label={`${username}'s tutor chats`} className="rounded-xl border border-border bg-surface p-3 text-xs">
      <h3 className="mb-2 flex items-center gap-1.5 text-[13px] font-medium">
        <AgentMark className="size-3.5 text-accent" /> Tutor chats
      </h3>
      <ul className="flex flex-wrap gap-1.5">
        {chats.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              onClick={() => void openChat(c.id)}
              className="flex max-w-72 items-center gap-1.5 rounded-md border border-border bg-surface-2 px-2 py-1 text-left hover:bg-hover"
              title={c.topology_name ? `${c.title} · on ${c.topology_name}` : c.title}
            >
              <MessageSquare className="size-3 shrink-0 text-fg-subtle" />
              <span className="truncate">{c.title}</span>
              <span className="shrink-0 text-2xs text-fg-subtle">{ago(c.updated_at)}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
