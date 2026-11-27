import { useState } from 'react';
import { Ellipsis, Eye, History, PencilLine, Plug, SquarePen, X } from 'lucide-react';
import { useAppStore } from '@/store';
import {
  Badge,
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  IconButton,
  Tooltip,
} from '@/ui';
import { MOD } from '@/lib/keyboard';
import { newChat, renameChat, setAutoApprove } from './actions';
import { useAgentStore, type ChatState } from './agentStore';
import { ChatList } from './ChatList';
import { ChatView } from './ChatView';
import { Composer } from './Composer';
import { AgentMark } from './AgentMark';
import { ConnectAgentDialog } from './ConnectAgentDialog';
import { useOwnerChats, useOwnerChatsLoader } from './useOwnerChats';

/** A short label on a chip, and the full prompt it puts in the message box. */
const STAFF_STARTERS: [string, string][] = [
  ['Build a lab', 'Build a lab with an IT and an OT subnet, a web server, a PLC and an attacker'],
  ['Check connectivity', 'Deploy this topology and check that every host can reach its gateway'],
  ['Write a tutorial', 'Write a short tutorial that walks a student through this lab'],
];
const TUTOR_STARTERS: [string, string][] = [
  ['Where do I start?', 'What should I look at first in this lab?'],
  ['Explain this lab', 'Explain how this topology is wired'],
  ['Why can’t I ping?', 'Why might my host fail to ping the server?'],
];

const INSTRUCTOR_READS = 'Your instructor can read your chats with the tutor.';

/** The agent sidebar: a chat (or the list of chats), and the composer. */
export function AgentPanel() {
  useOwnerChatsLoader();
  const chatId = useAppStore((s) => s.agentChatId);
  const listing = useAppStore((s) => s.agentListing);
  const setListing = useAppStore((s) => s.setAgentListing);
  const setAgentOpen = useAppStore((s) => s.setAgentOpen);
  const mode = useAgentStore((s) => s.status?.mode ?? null);
  const state = useAgentStore((s) => (chatId ? s.byId[chatId] : undefined));
  const theirs = useOwnerChats();
  const [renaming, setRenaming] = useState(false);
  const [connectOpen, setConnectOpen] = useState(false);
  const tutor = mode === 'tutor' || state?.chat.mode === 'tutor';
  const readOnly = !!state && !state.canSend;
  const othersChats = theirs?.chats.length ?? 0;

  return (
    <aside className="ae-agent-panel flex h-full min-w-0 flex-col border-l border-border bg-surface" aria-label="Agent">
      <header className="flex h-12 shrink-0 items-center gap-1 border-b border-border px-2">
        <AgentMark className="size-4 shrink-0 text-accent" />
        <div className="min-w-0 flex-1 pl-1">
          {listing ? (
            <div className="truncate text-[13px] font-medium text-fg">Chats</div>
          ) : (
            <ChatTitle
              chatId={chatId}
              title={state?.chat.title ?? (tutor ? 'Tutor' : 'Agent')}
              editing={renaming && !!state?.canSend}
              onEditingChange={setRenaming}
            />
          )}
          {!listing && state ? <Subtitle state={state} /> : null}
        </div>
        {mode === 'tutor' ? (
          <Tooltip content={INSTRUCTOR_READS} side="bottom">
            <span className="flex size-7 shrink-0 items-center justify-center text-fg-subtle" aria-label={INSTRUCTOR_READS}>
              <Eye className="size-3.5" />
            </span>
          </Tooltip>
        ) : null}
        <div className="flex shrink-0 items-center gap-0.5">
          <span className="relative">
            <IconButton
              label={listing ? 'Back to the chat' : othersChats ? `Chat history (${theirs?.username} has ${othersChats} here)` : 'Chat history'}
              size="icon-sm"
              variant={listing ? 'secondary' : 'ghost'}
              onClick={() => setListing(!listing)}
            >
              <History />
            </IconButton>
            {othersChats && !listing ? <span aria-hidden className="pointer-events-none absolute right-1 top-1 size-1.5 rounded-full bg-accent" /> : null}
          </span>
          <IconButton label="New chat" size="icon-sm" onClick={newChat}>
            <SquarePen />
          </IconButton>
          <PanelMenu state={listing ? undefined : state} onRename={() => setRenaming(true)} onConnect={() => setConnectOpen(true)} />
          <IconButton label="Close" shortcut={`${MOD}J`} size="icon-sm" onClick={() => setAgentOpen(false)}>
            <X />
          </IconButton>
        </div>
      </header>
      <ConnectAgentDialog open={connectOpen} onOpenChange={setConnectOpen} />

      {listing ? (
        <ChatList />
      ) : (
        <>
          {chatId ? <ChatView chatId={chatId} /> : <Welcome tutor={tutor} />}
          {readOnly ? (
            <div className="flex shrink-0 items-center gap-1.5 border-t border-border px-3 py-2 text-xs text-fg-muted">
              <Eye className="size-3.5" /> Read only
            </div>
          ) : (
            <Composer chatId={chatId} tutor={tutor} />
          )}
        </>
      )}
    </aside>
  );
}

/** Under the title: whose chat (someone else's), the tutor, the topology, Full auto. */
function Subtitle({ state }: { state: ChatState }) {
  const { chat, canSend } = state;
  const parts = [
    !canSend && chat.owner ? `${chat.owner.username}’s chat` : null,
    !canSend && chat.mode === 'tutor' ? 'tutor' : null,
    chat.topology_name ? `on ${chat.topology_name}` : null,
  ].filter(Boolean);
  const auto = canSend && chat.mode === 'full' && chat.auto_approve;
  if (!parts.length && !auto) return null;
  return (
    <div className="flex min-w-0 items-center gap-1.5 text-2xs text-fg-subtle">
      {auto ? (
        <Tooltip content="Full auto: destroying and publishing run without asking. Deletes always ask." side="bottom">
          <Badge tone="warning" className="shrink-0">Auto</Badge>
        </Tooltip>
      ) : null}
      <span className="truncate">{parts.join(' · ')}</span>
    </div>
  );
}

/** ⋯: the open chat's settings, connecting an external agent, the model. */
function PanelMenu({ state, onRename, onConnect }: { state?: ChatState; onRename: () => void; onConnect: () => void }) {
  const mode = useAgentStore((s) => s.status?.mode ?? null);
  const model = useAgentStore((s) => s.status?.model ?? null);
  const own = !!state?.canSend;
  const full = own && state?.chat.mode === 'full';
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <IconButton label="More" size="icon-sm">
          <Ellipsis />
        </IconButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        {full && state ? (
          <DropdownMenuCheckboxItem checked={state.chat.auto_approve} onCheckedChange={(v) => void setAutoApprove(state.chat.id, v === true)}>
            Full auto
            <span className="ml-auto pl-3 text-2xs text-fg-subtle">no approvals</span>
          </DropdownMenuCheckboxItem>
        ) : null}
        {own ? (
          <DropdownMenuItem onSelect={onRename}>
            <PencilLine /> Rename chat
          </DropdownMenuItem>
        ) : null}
        {mode === 'full' ? (
          <DropdownMenuItem onSelect={onConnect}>
            <Plug /> Connect an external agent…
          </DropdownMenuItem>
        ) : null}
        {model ? (
          <>
            {own || mode === 'full' ? <DropdownMenuSeparator /> : null}
            <DropdownMenuLabel className="font-normal text-fg-subtle">Model: {model}</DropdownMenuLabel>
          </>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function ChatTitle({ chatId, title, editing, onEditingChange }: { chatId: string | null; title: string; editing: boolean; onEditingChange: (v: boolean) => void }) {
  if (editing && chatId) {
    return (
      <input
        autoFocus
        defaultValue={title}
        onFocus={(e) => e.currentTarget.select()}
        onBlur={(e) => {
          const next = e.currentTarget.value.trim();
          if (next && next !== title) void renameChat(chatId, next);
          onEditingChange(false);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.currentTarget.blur();
          if (e.key === 'Escape') {
            e.currentTarget.value = title;
            e.currentTarget.blur();
          }
        }}
        className="w-full min-w-0 rounded border border-border bg-surface-2 px-1.5 py-0.5 text-[13px] text-fg outline-none focus:border-accent"
        aria-label="Chat title"
      />
    );
  }
  return (
    <div className="truncate text-[13px] font-medium text-fg" title={title}>
      {title}
    </div>
  );
}

/** A new chat: one line and a few chips that fill the message box. */
function Welcome({ tutor }: { tutor: boolean }) {
  const setDraft = useAgentStore((s) => s.setDraft);
  const openOwnerChats = useAppStore((s) => s.openOwnerChats);
  const theirs = useOwnerChats();
  const starters = tutor ? TUTOR_STARTERS : STAFF_STARTERS;
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4 overflow-y-auto px-4 py-6 text-center">
      <AgentMark className="size-6 text-accent" />
      <h2 className="text-sm font-medium text-fg">{tutor ? 'Stuck? Ask for a hint.' : 'What should we work on?'}</h2>
      <div className="flex flex-wrap justify-center gap-1.5">
        {starters.map(([label, prompt]) => (
          <button
            key={label}
            type="button"
            title={prompt}
            onClick={() => setDraft(prompt)}
            className="rounded-full border border-border bg-surface-2 px-3 py-1 text-xs text-fg-muted hover:border-border-strong hover:bg-hover hover:text-fg"
          >
            {label}
          </button>
        ))}
      </div>
      {tutor ? <p className="text-2xs text-fg-subtle">{INSTRUCTOR_READS}</p> : null}
      {theirs && theirs.chats.length > 0 ? (
        <button type="button" onClick={openOwnerChats} className="text-2xs text-fg-subtle hover:text-fg">
          {theirs.username} has {theirs.chats.length} chat{theirs.chats.length === 1 ? '' : 's'} here · <span className="text-accent">View</span>
        </button>
      ) : null}
    </div>
  );
}
