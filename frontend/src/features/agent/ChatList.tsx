import { useState } from 'react';
import { MessageSquare, Trash2 } from 'lucide-react';
import { useAppStore } from '@/store';
import { EmptyState, IconButton, Spinner } from '@/ui';
import { ago } from '@/lib/time';
import { cn } from '@/lib/cn';
import { deleteChat, openChat } from './actions';
import { useAgentStore } from './agentStore';

/** The user's saved chats; with a topology open, its chats first (or only). */
export function ChatList({ onPicked }: { onPicked: () => void }) {
  const chats = useAgentStore((s) => s.chats);
  const backendId = useAppStore((s) => s.backendId);
  const [onlyHere, setOnlyHere] = useState(false);
  const [confirm, setConfirm] = useState<string | null>(null);

  if (chats === null) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner />
      </div>
    );
  }
  const shown = onlyHere && backendId ? chats.filter((c) => c.topology_id === backendId) : chats;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {backendId ? (
        <div className="flex shrink-0 gap-1 border-b border-border px-2 py-1.5 text-xs">
          {[false, true].map((here) => (
            <button
              key={String(here)}
              type="button"
              onClick={() => setOnlyHere(here)}
              className={cn('rounded px-2 py-0.5', onlyHere === here ? 'bg-active text-fg' : 'text-fg-muted hover:bg-hover')}
            >
              {here ? 'This topology' : 'All chats'}
            </button>
          ))}
        </div>
      ) : null}
      {shown.length === 0 ? (
        <EmptyState icon={<MessageSquare />} title="No chats yet" description="Ask the agent something to start one." className="flex-1" />
      ) : (
        <ul className="min-h-0 flex-1 overflow-y-auto p-1.5">
          {shown.map((c) => (
            <li key={c.id} className="group relative">
              <button
                type="button"
                onClick={() => {
                  onPicked();
                  void openChat(c.id);
                }}
                className="flex w-full flex-col gap-0.5 rounded-md px-2.5 py-2 text-left hover:bg-hover"
              >
                <span className="flex min-w-0 items-center gap-1.5 pr-7 text-[13px] text-fg">
                  {c.active_job_id ? <Spinner className="size-3 shrink-0 text-accent" /> : null}
                  <span className="truncate">{c.title}</span>
                </span>
                <span className="truncate text-2xs text-fg-subtle">
                  {c.topology_name ? `${c.topology_name} · ` : ''}
                  {ago(c.updated_at)}
                  {c.mode === 'tutor' ? ' · tutor' : ''}
                </span>
              </button>
              <IconButton
                label={confirm === c.id ? 'Click again to delete' : 'Delete chat'}
                size="icon-xs"
                variant={confirm === c.id ? 'danger' : 'ghost'}
                className={cn('absolute right-1.5 top-2', confirm === c.id ? '' : 'opacity-0 group-hover:opacity-100 focus-visible:opacity-100')}
                onClick={() => {
                  if (confirm === c.id) {
                    setConfirm(null);
                    void deleteChat(c.id);
                  } else {
                    setConfirm(c.id);
                  }
                }}
                onBlur={() => setConfirm((v) => (v === c.id ? null : v))}
              >
                <Trash2 />
              </IconButton>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
