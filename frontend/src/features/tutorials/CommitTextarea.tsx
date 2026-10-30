import { useLayoutEffect, useRef, useState } from 'react';
import { Textarea } from '@/ui';
import { cn } from '@/lib/cn';

export interface CommitTextareaProps extends Omit<React.ComponentProps<'textarea'>, 'value' | 'onChange'> {
  value: string;
  onCommit: (value: string) => void;
}

/** Multi-line twin of the inspector's CommitInput: writes to the store on blur
 *  (one undo step per edit), Esc reverts. Grows with its content. */
export function CommitTextarea({ value, onCommit, className, onBlur, onKeyDown, ...props }: CommitTextareaProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [draft, setDraft] = useState(value);
  const [prev, setPrev] = useState(value);
  if (prev !== value) {
    setPrev(value);
    setDraft(value);
  }

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight + 2}px`;
  }, [draft]);

  const commit = () => {
    const v = draft.replace(/\s+$/, '');
    if (v !== value) onCommit(v);
  };

  return (
    <Textarea
      ref={ref}
      rows={1}
      {...props}
      className={cn('min-h-0 resize-none overflow-hidden', className)}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={(e) => { commit(); onBlur?.(e); }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          setDraft(value);
          // Let the revert render before blur commits it.
          requestAnimationFrame(() => ref.current?.blur());
          return;
        }
        onKeyDown?.(e);
      }}
    />
  );
}
