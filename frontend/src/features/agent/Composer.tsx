import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router';
import { ArrowUp, Network, Square, TriangleAlert } from 'lucide-react';
import { useAppShallow } from '@/store/selectors';
import { IconButton } from '@/ui';
import { cn } from '@/lib/cn';
import { sendMessage, stopRun } from './actions';
import { useAgentStore } from './agentStore';

/** What the next message is about: the open topology (and scope, selection), an
 *  unsaved draft the agent can't see, or nothing (the library). */
function useContext(): { label: string; warn: boolean } | null {
  const { pathname } = useLocation();
  const { backendId, name, selected } = useAppShallow((s) => ({
    backendId: s.backendId,
    name: s.backendName ?? s.topology.name ?? '',
    selected: s.selection.nodeIds.length,
  }));
  if (!pathname.startsWith('/t/')) return null;
  if (!backendId) return { label: 'Unsaved draft: save it so the agent can see it', warn: true };
  const where = pathname.includes('/subnet/') ? ' · subnet' : pathname.includes('/site/') ? ' · site' : '';
  return { label: `${name || 'Topology'}${where}${selected ? ` · ${selected} selected` : ''}`, warn: false };
}

function resize(el: HTMLTextAreaElement) {
  el.style.height = 'auto';
  el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
}

export function Composer({ chatId, tutor }: { chatId: string | null; tutor: boolean }) {
  const text = useAgentStore((s) => s.draft);
  const setText = useAgentStore((s) => s.setDraft);
  const ref = useRef<HTMLTextAreaElement>(null);
  const running = useAgentStore((s) => (chatId ? !!s.byId[chatId]?.run : false));
  const busy = useAgentStore((s) => (chatId ? !!s.byId[chatId]?.sending : false));
  const context = useContext();

  // Filled from outside (a starter chip): fit it, and put the cursor at its end.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    resize(el);
    if (text && document.activeElement !== el) {
      el.focus();
      el.setSelectionRange(text.length, text.length);
    }
  }, [text]);

  const submit = () => {
    const t = text.trim();
    if (!t || busy) return;
    setText('');
    void sendMessage(chatId, t);
    ref.current?.focus();
  };

  return (
    <div className="shrink-0 border-t border-border bg-surface p-2">
      <div className="flex flex-col gap-1 rounded-lg border border-border bg-surface-2 p-1.5 focus-within:border-accent">
        <textarea
          ref={ref}
          value={text}
          rows={1}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder={running ? 'Add to what it’s doing…' : tutor ? 'Ask for a hint…' : 'Ask anything…'}
          aria-label="Message the agent"
          className="max-h-44 min-h-7 resize-none bg-transparent px-1.5 py-1 text-[13px] leading-snug text-fg outline-none placeholder:text-fg-subtle"
        />
        <div className="flex items-center gap-1.5">
          {context ? (
            <span
              title={context.label}
              className={cn(
                'flex min-w-0 items-center gap-1 rounded px-1.5 py-0.5 text-2xs',
                context.warn ? 'bg-warning-soft text-warning' : 'text-fg-subtle',
              )}
            >
              {context.warn ? <TriangleAlert className="size-3 shrink-0" /> : <Network className="size-3 shrink-0" />}
              <span className="truncate">{context.label}</span>
            </span>
          ) : null}
          <span className="ml-auto flex shrink-0 items-center gap-1">
            {running && chatId ? (
              <IconButton label="Stop the agent" size="icon-sm" variant="danger-soft" onClick={() => void stopRun(chatId)}>
                <Square />
              </IconButton>
            ) : null}
            <IconButton
              label="Send"
              tooltip="Send (Enter)"
              size="icon-sm"
              variant="primary"
              disabled={!text.trim() || busy}
              onClick={submit}
              className={cn(!text.trim() && 'opacity-60')}
            >
              <ArrowUp />
            </IconButton>
          </span>
        </div>
      </div>
    </div>
  );
}
