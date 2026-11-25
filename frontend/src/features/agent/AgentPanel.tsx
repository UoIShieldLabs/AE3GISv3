import { useState } from 'react';
import { Eye, History, SquarePen, X } from 'lucide-react';
import { useAppStore } from '@/store';
import { Badge, IconButton, Switch, Tooltip } from '@/ui';
import { MOD } from '@/lib/keyboard';
import { newChat, renameChat, sendMessage, setAutoApprove } from './actions';
import { useAgentStore } from './agentStore';
import { ChatList } from './ChatList';
import { ChatView } from './ChatView';
import { Composer } from './Composer';
import { AgentMark } from './AgentMark';
import { ConnectAgentDialog } from './ConnectAgentDialog';

const STAFF_STARTERS = [
  'Build a lab with an IT and an OT subnet, a web server, a PLC and an attacker',
  'Deploy this topology and check that every host can reach its gateway',
  'Capture traffic on the busiest link for 30 seconds and summarize it',
  'Write a short tutorial that walks a student through this lab',
];
const TUTOR_STARTERS = ['What should I look at first in this lab?', 'Explain how this topology is wired', 'Why might my host fail to ping the server?'];

/** The agent sidebar: a chat (or the list of chats), and the composer. */
export function AgentPanel() {
  const chatId = useAppStore((s) => s.agentChatId);
  const setAgentOpen = useAppStore((s) => s.setAgentOpen);
  const mode = useAgentStore((s) => s.status?.mode ?? null);
  const model = useAgentStore((s) => s.status?.model ?? null);
  const state = useAgentStore((s) => (chatId ? s.byId[chatId] : undefined));
  const [listing, setListing] = useState(false);
  const tutor = mode === 'tutor' || state?.chat.mode === 'tutor';
  const readOnly = !!state && !state.canSend;

  return (
    <aside className="ae-agent-panel flex h-full min-w-0 flex-col border-l border-border bg-surface" aria-label="Agent">
      <header className="flex h-12 shrink-0 items-center gap-1 border-b border-border px-2">
        <AgentMark className="size-4 shrink-0 text-accent" />
        <ChatTitle chatId={chatId} title={listing ? 'Chats' : (state?.chat.title ?? (tutor ? 'Tutor' : 'Agent'))} editable={!listing && !!state?.canSend} />
        <div className="ml-auto flex shrink-0 items-center gap-0.5">
          <IconButton label={listing ? 'Back to the chat' : 'Chat history'} size="icon-sm" variant={listing ? 'secondary' : 'ghost'} onClick={() => setListing((v) => !v)}>
            <History />
          </IconButton>
          <IconButton
            label="New chat"
            size="icon-sm"
            onClick={() => {
              setListing(false);
              newChat();
            }}
          >
            <SquarePen />
          </IconButton>
          <IconButton label="Close" shortcut={`${MOD}J`} size="icon-sm" onClick={() => setAgentOpen(false)}>
            <X />
          </IconButton>
        </div>
      </header>

      {listing ? (
        <ChatList onPicked={() => setListing(false)} />
      ) : (
        <>
          {state ? <ChatBar chatId={state.chat.id} /> : null}
          {tutor && !readOnly ? (
            <div className="shrink-0 border-b border-border bg-info-soft px-3 py-1.5 text-2xs text-info">Your instructor can read your chats with the tutor.</div>
          ) : null}
          {chatId ? (
            <ChatView chatId={chatId} />
          ) : (
            <Welcome tutor={tutor} model={model} />
          )}
          {readOnly ? (
            <div className="flex shrink-0 items-center gap-1.5 border-t border-border px-3 py-2 text-xs text-fg-muted">
              <Eye className="size-3.5" /> {state?.chat.owner?.username ?? 'Someone'}’s chat — read only
            </div>
          ) : (
            <Composer chatId={chatId} tutor={tutor} />
          )}
        </>
      )}
    </aside>
  );
}

function ChatTitle({ chatId, title, editable }: { chatId: string | null; title: string; editable: boolean }) {
  const [draft, setDraft] = useState<string | null>(null);
  if (draft !== null && chatId) {
    return (
      <input
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => {
          void renameChat(chatId, draft);
          setDraft(null);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.currentTarget.blur();
          if (e.key === 'Escape') setDraft(null);
        }}
        className="min-w-0 flex-1 rounded border border-border bg-surface-2 px-1.5 py-0.5 text-[13px] text-fg outline-none focus:border-accent"
        aria-label="Chat title"
      />
    );
  }
  return (
    <button
      type="button"
      disabled={!editable}
      onDoubleClick={() => setDraft(title)}
      title={editable ? 'Double-click to rename' : undefined}
      className="min-w-0 truncate text-left text-[13px] font-medium text-fg disabled:cursor-default"
    >
      {title}
    </button>
  );
}

/** A chat's settings line: auto-approve (its owner, full agent), whose it is. */
function ChatBar({ chatId }: { chatId: string }) {
  const state = useAgentStore((s) => s.byId[chatId]);
  if (!state) return null;
  const { chat, canSend } = state;
  if (!canSend) {
    return (
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-3 py-1.5 text-2xs text-fg-muted">
        <Badge tone="outline">{chat.mode === 'tutor' ? 'Tutor' : 'Agent'}</Badge>
        {chat.topology_name ? <span className="truncate">on {chat.topology_name}</span> : null}
      </div>
    );
  }
  if (chat.mode !== 'full') return null;
  return (
    <div className="flex shrink-0 items-center gap-2 border-b border-border px-3 py-1.5 text-2xs text-fg-muted">
      <Tooltip content="Destroying labs and publishing run without asking. Deletes always ask." side="bottom">
        <label className="flex cursor-pointer items-center gap-1.5">
          <Switch checked={chat.auto_approve} onCheckedChange={(v) => void setAutoApprove(chatId, v)} aria-label="Auto-approve risky actions" />
          Full auto
        </label>
      </Tooltip>
      {chat.topology_name ? <span className="ml-auto truncate">on {chat.topology_name}</span> : null}
    </div>
  );
}

function Welcome({ tutor, model }: { tutor: boolean; model: string | null }) {
  const starters = tutor ? TUTOR_STARTERS : STAFF_STARTERS;
  const [connectOpen, setConnectOpen] = useState(false);
  return (
    <div className="flex min-h-0 flex-1 flex-col justify-end gap-3 overflow-y-auto px-3 py-4">
      <div>
        <h2 className="text-sm font-semibold text-fg">{tutor ? 'Your lab tutor' : 'What should the agent do?'}</h2>
        <p className="mt-1 text-xs leading-relaxed text-fg-muted">
          {tutor
            ? 'It can read your topology and your lab and give hints. It never changes anything; you do the work.'
            : 'It acts as you: builds and edits topologies, deploys labs, runs commands in nodes, captures traffic and writes tutorials. Destroying, publishing and deleting ask you first.'}
        </p>
        {model ? <p className="mt-1 text-2xs text-fg-subtle">Model: {model}</p> : null}
      </div>
      <div className="flex flex-col gap-1.5">
        {starters.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => void sendMessage(null, s)}
            className="rounded-md border border-border bg-surface-2 px-2.5 py-1.5 text-left text-xs text-fg hover:border-border-strong hover:bg-hover"
          >
            {s}
          </button>
        ))}
      </div>
      {!tutor ? (
        <>
          <button type="button" onClick={() => setConnectOpen(true)} className="self-start text-2xs text-fg-subtle underline-offset-2 hover:text-fg hover:underline">
            Use these tools from Claude Code or OpenCode…
          </button>
          <ConnectAgentDialog open={connectOpen} onOpenChange={setConnectOpen} />
        </>
      ) : null}
    </div>
  );
}
