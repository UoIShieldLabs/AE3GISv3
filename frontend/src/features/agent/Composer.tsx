import { useRef, useState } from 'react';
import { useLocation } from 'react-router';
import { ArrowUp, Square } from 'lucide-react';
import { useAppShallow } from '@/store/selectors';
import { IconButton } from '@/ui';
import { cn } from '@/lib/cn';
import { sendMessage, stopRun } from './actions';
import { useAgentStore } from './agentStore';

/** Where the next message will be sent from: the open topology, scope, selection. */
function useContextLabel(): string {
  const { pathname } = useLocation();
  const { backendId, name, selected } = useAppShallow((s) => ({
    backendId: s.backendId,
    name: s.backendName ?? s.topology.name ?? '',
    selected: s.selection.nodeIds.length,
  }));
  if (!pathname.startsWith('/t/') || !backendId) return pathname === '/' ? 'Library' : 'Unsaved draft (save it to let the agent see it)';
  const where = pathname.includes('/subnet/') ? ' · in a subnet' : pathname.includes('/site/') ? ' · in a site' : '';
  return `${name || 'Topology'}${where}${selected ? ` · ${selected} selected` : ''}`;
}

export function Composer({ chatId, tutor }: { chatId: string | null; tutor: boolean }) {
  const [text, setText] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);
  const running = useAgentStore((s) => (chatId ? !!s.byId[chatId]?.run : false));
  const busy = useAgentStore((s) => (chatId ? !!s.byId[chatId]?.sending : false));
  const context = useContextLabel();

  const submit = () => {
    const t = text.trim();
    if (!t || busy) return;
    setText('');
    void sendMessage(chatId, t);
    ref.current?.focus();
  };

  return (
    <div className="shrink-0 border-t border-border bg-surface p-2">
      <div className="mb-1 truncate px-1 text-2xs text-fg-subtle" title={context}>{context}</div>
      <div className="flex items-end gap-1.5 rounded-lg border border-border bg-surface-2 p-1.5 focus-within:border-accent">
        <textarea
          ref={ref}
          value={text}
          rows={1}
          onChange={(e) => {
            setText(e.target.value);
            const el = e.target;
            el.style.height = 'auto';
            el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder={
            running ? 'Add to what it’s doing…' : tutor ? 'Ask for a hint or an explanation…' : 'Ask the agent to build, run or explain…'
          }
          aria-label="Message the agent"
          className="max-h-44 min-h-7 flex-1 resize-none bg-transparent px-1.5 py-1 text-[13px] leading-snug text-fg outline-none placeholder:text-fg-subtle"
        />
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
      </div>
    </div>
  );
}
