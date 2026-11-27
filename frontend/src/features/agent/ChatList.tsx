import { useState } from 'react';
import { MessageSquare, Trash2 } from 'lucide-react';
import type * as api from '@/api/client';
import { useAppStore } from '@/store';
import type { AgentListScope } from '@/store/types';
import { EmptyState, IconButton, Spinner } from '@/ui';
import { ago } from '@/lib/time';
import { cn } from '@/lib/cn';
import { deleteChat, openChat } from './actions';
import { useAgentStore } from './agentStore';
import { useOwnerChats, useOwnerTarget } from './useOwnerChats';

/** Saved chats: yours, yours on the open topology, or (on someone else's
 *  topology, e.g. a student's) theirs there, read-only. */
export function ChatList() {
  const mine = useAgentStore((s) => s.chats);
  const backendId = useAppStore((s) => s.backendId);
  const wanted = useAppStore((s) => s.agentListScope);
  const setScope = useAppStore((s) => s.setAgentListScope);
  const target = useOwnerTarget();
  const theirs = useOwnerChats();

  // A scope that doesn't apply here falls back to all of yours.
  const scope: AgentListScope = wanted === 'owner' && !target ? 'all' : wanted === 'here' && !backendId ? 'all' : wanted;
  const tabs: { id: AgentListScope; label: string }[] = [
    { id: 'all', label: 'All chats' },
    ...(backendId ? [{ id: 'here' as const, label: 'This topology' }] : []),
    ...(target ? [{ id: 'owner' as const, label: `${target.username}’s` }] : []),
  ];

  const chats = scope === 'owner' ? theirs?.chats ?? null : scope === 'here' ? mine?.filter((c) => c.topology_id === backendId) ?? null : mine;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {tabs.length > 1 ? (
        <div role="tablist" aria-label="Which chats" className="flex shrink-0 gap-1 border-b border-border px-2 py-1.5 text-xs">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={scope === t.id}
              onClick={() => setScope(t.id)}
              className={cn('truncate rounded px-2 py-0.5', scope === t.id ? 'bg-active text-fg' : 'text-fg-muted hover:bg-hover')}
            >
              {t.label}
              {t.id === 'owner' && theirs?.chats.length ? <span className="ml-1 text-fg-subtle">{theirs.chats.length}</span> : null}
            </button>
          ))}
        </div>
      ) : null}
      {chats === null ? (
        <div className="flex flex-1 items-center justify-center">
          <Spinner />
        </div>
      ) : chats.length === 0 ? (
        <EmptyState
          icon={<MessageSquare />}
          title="No chats yet"
          description={scope === 'owner' ? `${target?.username} hasn’t asked the tutor about this topology.` : undefined}
          className="flex-1"
        />
      ) : (
        <ul className="min-h-0 flex-1 overflow-y-auto p-1.5">
          {chats.map((c) => (
            <ChatRow key={c.id} chat={c} deletable={scope !== 'owner'} showTopology={scope === 'all'} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ChatRow({ chat: c, deletable, showTopology }: { chat: api.AgentChat; deletable: boolean; showTopology: boolean }) {
  const [confirm, setConfirm] = useState(false);
  return (
    <li className="group relative">
      <button type="button" onClick={() => void openChat(c.id)} className="flex w-full flex-col gap-0.5 rounded-md px-2.5 py-2 text-left hover:bg-hover">
        <span className="flex min-w-0 items-center gap-1.5 pr-7 text-[13px] text-fg">
          {c.active_job_id ? <Spinner className="size-3 shrink-0 text-accent" /> : null}
          <span className="truncate">{c.title}</span>
        </span>
        <span className="truncate text-2xs text-fg-subtle">
          {showTopology && c.topology_name ? `${c.topology_name} · ` : ''}
          {ago(c.updated_at)}
        </span>
      </button>
      {deletable ? (
        <IconButton
          label={confirm ? 'Click again to delete' : 'Delete chat'}
          size="icon-xs"
          variant={confirm ? 'danger' : 'ghost'}
          className={cn('absolute right-1.5 top-2', confirm ? '' : 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100')}
          onClick={() => {
            if (confirm) {
              setConfirm(false);
              void deleteChat(c.id);
            } else {
              setConfirm(true);
            }
          }}
          onBlur={() => setConfirm(false)}
        >
          <Trash2 />
        </IconButton>
      ) : null}
    </li>
  );
}
